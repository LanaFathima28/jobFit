from app.schemas.extraction_schemas import (
    CandidateExtractionSchema,
    JobExtractionSchema,
)

CANDIDATE_EXTRACTION_SYSTEM_PROMPT = """You are an expert AI resume parser and talent intelligence specialist.
Your task is to analyze the provided raw resume text and extract clean, structured candidate details into the specified tool schema.

CRITICAL EXTRACTION DIRECTIVES:
1. FULL NAME: Extract the candidate's actual full name accurately from the header or top section of the resume.
2. TOTAL YEARS OF EXPERIENCE: Calculate the total numeric years of work experience derived by summing distinct, non-overlapping employment periods in the candidate's work history.
   - Example: 2018-01 to 2020-01 (2 years) + 2020-06 to 2023-06 (3 years) = 5.0 years.
   - Do NOT double count overlapping positions (e.g. concurrent freelance work or internships during school).
   - If currently employed ("Present" or "Current"), calculate up to the current date.
   - Output a single numeric float rounded to 1 decimal place.
3. SKILLS: Extract technical skills, programming languages, frameworks, databases, cloud tools, methodologies, and key soft skills.
   - Use canonical skill names (e.g. "React" instead of "ReactJS", "Node.js" instead of "NodeJS", "Python" instead of "Python3", "PostgreSQL" instead of "Postgres").
4. WORK HISTORY: Extract each employment position into work_history list:
   - title: Official job title.
   - company: Company/Organization name.
   - start_date: Formatted as YYYY-MM or YYYY.
   - end_date: Formatted as YYYY-MM, YYYY, or "Present".
   - description: Summary of key duties, tech stack, and achievements.
5. EDUCATION: Extract degrees, institutions, fields of study, and graduation years.
6. CERTIFICATIONS: Extract formal professional certifications or credentials.

Always call the `extract_candidate_profile` tool with the extracted data. Do NOT include markdown commentary or preamble outside the tool call."""


JOB_EXTRACTION_SYSTEM_PROMPT = """You are an expert HR technologist and technical recruiter.
Your task is to analyze the provided job description text and extract structured job requirements into the specified tool schema.

CRITICAL EXTRACTION DIRECTIVES:
1. JOB TITLE: Extract the official job title.
2. REQUIRED SKILLS: Extract technical tools, programming languages, frameworks, platforms, and mandatory skills required for the role.
3. PREFERRED SKILLS: Extract nice-to-have, optional, or preferred skills if explicitly distinguished from mandatory requirements. If not distinguished, leave preferred_skills empty.
4. MIN YEARS EXPERIENCE: Extract the minimum required years of experience as a numeric float (e.g., 3.0 or 5.0). If a range is given (e.g., "3-5 years"), extract the minimum (3.0). If not specified, set to 0.0.
5. EDUCATION REQUIREMENT: Extract any specified degree requirements (e.g. "Bachelor's degree in Computer Science or equivalent").
6. RESPONSIBILITIES: Extract the key duties, tasks, and responsibilities for this role as a list of strings.

Always call the `extract_job_details` tool with the extracted data. Do NOT include markdown commentary or preamble outside the tool call."""


CANDIDATE_EXTRACTION_TOOL = {
    "name": "extract_candidate_profile",
    "description": "Extract structured candidate profile details from raw resume text.",
    "input_schema": CandidateExtractionSchema.model_json_schema()
}

JOB_EXTRACTION_TOOL = {
    "name": "extract_job_details",
    "description": "Extract structured job posting requirements from raw job description text.",
    "input_schema": JobExtractionSchema.model_json_schema()
}
