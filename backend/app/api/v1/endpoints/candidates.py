import pathlib
from typing import List, Union, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateResponse
from app.services.extraction_service import extract_text_from_file_bytes, ExtractionStatus
from app.services.storage import storage_service
from app.core.security import verify_api_key
from app.core.rate_limiter import check_rate_limit
from app.worker.tasks import process_candidate_file_pipeline_task

router = APIRouter(prefix="/candidates", tags=["Candidates"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {"pdf", "docx"}


class CandidateTaskItem(BaseModel):
    candidate_id: UUID
    original_filename: str
    task_id: str


class BulkUploadProcessResponse(BaseModel):
    message: str
    candidate_tasks: List[CandidateTaskItem]


def _process_single_candidate_file(file: UploadFile, file_bytes: bytes, db: Session) -> Candidate:
    filename = file.filename or "uploaded_resume.pdf"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format '.{ext}' for file '{filename}'. Only PDF and DOCX files are allowed."
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' exceeds maximum allowed size limit of 5MB."
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' is empty (0 bytes)."
        )

    file_path, file_size = storage_service.save_file(file_bytes, filename, category="candidates")
    extraction_result = extract_text_from_file_bytes(file_bytes, filename)
    candidate_name = pathlib.Path(filename).stem.replace("_", " ").replace("-", " ").title()

    candidate = Candidate(
        name=candidate_name,
        raw_text=extraction_result.text if extraction_result.status == ExtractionStatus.SUCCESS else None,
        original_filename=filename,
        file_type=ext,
        file_path=file_path,
        file_size=file_size,
        extraction_status=extraction_result.status.value,
        extraction_error=extraction_result.error_message
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/upload", response_model=List[CandidateResponse], status_code=status.HTTP_201_CREATED)
async def upload_candidate_resumes(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Upload single or bulk candidate resumes (PDF or DOCX).
    Saves original file to storage, extracts raw text, and persists candidate with ingestion metadata.
    """
    check_rate_limit(request, limit=30, window_seconds=60)

    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No resume files uploaded.")

    created_candidates = []
    for upload_file in upload_list:
        file_bytes = await upload_file.read()
        candidate = _process_single_candidate_file(upload_file, file_bytes, db)
        created_candidates.append(candidate)

    return created_candidates


@router.post("/upload-and-process", response_model=BulkUploadProcessResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_process_candidate_resumes(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Phase 7 Orchestration Endpoint: Bulk upload candidate resumes and kick off async background pipeline per file.
    Per file: Saves file -> Creates Candidate record -> Dispatches Async Pipeline Task (Extraction -> Structured Profile -> Embedding).
    Returns immediately with task IDs for polling via GET /api/tasks/{task_id}/status.
    """
    check_rate_limit(request, limit=20, window_seconds=60)

    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file and file not in upload_list:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No resume files uploaded.")

    candidate_tasks = []

    for upload_file in upload_list:
        filename = upload_file.filename or "uploaded_resume.pdf"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format '.{ext}' for file '{filename}'. Only PDF and DOCX allowed."
            )

        file_bytes = await upload_file.read()
        if len(file_bytes) > MAX_FILE_SIZE_BYTES or len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{filename}' invalid size (0 bytes or exceeds 5MB)."
            )

        file_path, file_size = storage_service.save_file(file_bytes, filename, category="candidates")
        cand_name = pathlib.Path(filename).stem.replace("_", " ").replace("-", " ").title()

        candidate = Candidate(
            name=cand_name,
            raw_text=None,
            original_filename=filename,
            file_type=ext,
            file_path=file_path,
            file_size=file_size,
            extraction_status="pending",
            structured_extraction_status="pending"
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        try:
            async_task = process_candidate_file_pipeline_task.delay(str(candidate.id))
            task_id = async_task.id
        except Exception:
            import uuid
            task_id = str(uuid.uuid4())

        candidate_tasks.append(
            CandidateTaskItem(
                candidate_id=candidate.id,
                original_filename=filename,
                task_id=task_id
            )
        )

    return BulkUploadProcessResponse(
        message=f"Bulk upload initiated for {len(candidate_tasks)} files. Processing asynchronously.",
        candidate_tasks=candidate_tasks
    )


@router.get("", response_model=List[CandidateResponse])
def list_candidates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    List all candidates with upload and extraction status.
    """
    candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get stored candidate record by ID including raw_text and ingestion metadata.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate


@router.post("/{candidate_id}/extract", response_model=CandidateResponse)
def extract_candidate_structured_data_endpoint(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Triggers structured profile extraction for a candidate whose raw_text is already stored.
    Saves extracted JSON to structured_data and updates structured_extraction_status and debug_raw_llm_output.
    """
    from app.services.structured_extraction import extract_candidate_structured_data

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if not candidate.raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate has no stored raw_text to extract from."
        )

    structured_dict, ext_status, debug_llm = extract_candidate_structured_data(candidate.raw_text)

    candidate.structured_data = structured_dict
    candidate.structured_extraction_status = ext_status
    candidate.debug_raw_llm_output = debug_llm

    if structured_dict.get("full_name") and structured_dict["full_name"].strip():
        candidate.name = structured_dict["full_name"].strip()

    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/extract-batch", response_model=List[CandidateResponse])
def batch_extract_candidates_endpoint(
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Synchronously extracts structured data for all candidates with 'pending' structured extraction status.
    """
    from app.services.structured_extraction import extract_candidate_structured_data

    pending_candidates = db.query(Candidate).filter(
        (Candidate.structured_extraction_status == "pending") | (Candidate.structured_extraction_status == None)
    ).all()

    processed_candidates = []
    for candidate in pending_candidates:
        if not candidate.raw_text:
            candidate.structured_extraction_status = "failed"
            candidate.debug_raw_llm_output = "No raw_text available for extraction."
            db.commit()
            processed_candidates.append(candidate)
            continue

        structured_dict, ext_status, debug_llm = extract_candidate_structured_data(candidate.raw_text)
        candidate.structured_data = structured_dict
        candidate.structured_extraction_status = ext_status
        candidate.debug_raw_llm_output = debug_llm

        if structured_dict.get("full_name") and structured_dict["full_name"].strip():
            candidate.name = structured_dict["full_name"].strip()

        db.commit()
        db.refresh(candidate)
        processed_candidates.append(candidate)

    return processed_candidates


@router.post("/{candidate_id}/embed", response_model=CandidateResponse)
def embed_candidate_endpoint(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Generates and stores embedding_input and 1536-dim vector embedding for one candidate.
    """
    from app.services.embedding_service import build_candidate_embedding_input, generate_text_embedding

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    embedding_input = build_candidate_embedding_input(candidate.structured_data, candidate.raw_text)
    vector = generate_text_embedding(embedding_input)

    candidate.embedding_input = embedding_input
    candidate.embedding = vector

    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/embed-batch", response_model=List[CandidateResponse])
def batch_embed_candidates_endpoint(
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Batch generates vector embeddings for all candidates that have structured_data/raw_text but no embedding yet.
    """
    from app.services.embedding_service import build_candidate_embedding_input, generate_batch_embeddings

    unembedded_candidates = db.query(Candidate).filter(
        Candidate.embedding == None
    ).all()

    if not unembedded_candidates:
        return []

    inputs = []
    for cand in unembedded_candidates:
        inp = build_candidate_embedding_input(cand.structured_data, cand.raw_text)
        cand.embedding_input = inp
        inputs.append(inp)

    vectors = generate_batch_embeddings(inputs)

    for cand, vec in zip(unembedded_candidates, vectors):
        cand.embedding = vec

    db.commit()
    for cand in unembedded_candidates:
        db.refresh(cand)

    return unembedded_candidates


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: UUID,
    db: Session = Depends(get_db),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Delete a candidate.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    db.delete(candidate)
    db.commit()
    return None
