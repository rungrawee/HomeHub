const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

async function request(path, signal) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch(`${API_URL}${path}`, { signal });
      if (response.ok) return response.json();
      if (response.status < 500 || attempt === 1) {
        throw new Error(`API request failed with status ${response.status}`);
      }
    } catch (error) {
      if (error.name === "AbortError" || attempt === 1) throw error;
    }
  }
  throw new Error("API request failed");
}

export async function getFilterOptions(path, params = {}, signal) {
  const query = new URLSearchParams(params);
  const suffix = query.size ? `?${query}` : "";
  const response = await request(`/filters/${path}${suffix}`, signal);
  return response.items || [];
}

export async function searchAssets(filters, signal) {
  const query = new URLSearchParams({ page: "1", page_size: "100" });
  for (const key of ["province", "amphur", "tambon"]) {
    if (filters[key]) query.set(key, filters[key]);
  }
  return request(`/assets?${query}`, signal);
}
