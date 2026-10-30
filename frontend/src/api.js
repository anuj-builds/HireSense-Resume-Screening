
const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health/`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json();
}

export async function getResumes() {
  const response = await fetch(`${API_BASE_URL}/resumes/`);
  if (!response.ok) throw new Error("Failed to fetch resumes");
  return response.json();
}

export async function getRankedCandidates(jobId) {
  const response = await fetch(
    `${API_BASE_URL}/screening/${jobId}/rank`
  );
  if (!response.ok) throw new Error("Failed to fetch screening results");
  return response.json();
}

export async function updateShortlist(jobId, resumeId, status) {
  const response = await fetch(
    `${API_BASE_URL}/screening/${jobId}/shortlist/${resumeId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }
  );

  if (!response.ok) throw new Error("Failed to update shortlist");
  return response.json();
}


export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("files", file);

  const response = await fetch(`${API_BASE_URL}/resumes/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Resume upload failed");
  }

  return data;
}
