/**
 * API Service for MDMS Backend
 * Centralized API calls to the backend
 */

// If VITE_API_BASE_URL is set, use it. Otherwise use relative '/api' so Vite proxy works in dev.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Generic fetch wrapper with error handling
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
      const text = await response.text();
      let errorMessage = text;
      try {
        const errorData = JSON.parse(text);
        errorMessage = errorData.detail || JSON.stringify(errorData);
      } catch {
        // keep text
      }
      throw new Error(errorMessage || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    throw error;
  }
}

/**
 * Upload files to backend
 */
export async function uploadComplaints(files) {
  const formData = new FormData();
  
  // Add all files to FormData
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE_URL}/api/complaints/batch`, {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Upload failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Get all tickets
 */
export async function getTickets(filters = {}) {
  const params = new URLSearchParams();
  
  if (filters.status) params.append('status', filters.status);
  if (filters.issue_type) params.append('issue_type', filters.issue_type);
  
  const queryString = params.toString();
  const endpoint = `/api/complaints/tickets${queryString ? `?${queryString}` : ''}`;
  
  return apiRequest(endpoint);
}

/**
 * Get ticket by ID
 */
export async function getTicketById(ticketId) {
  return apiRequest(`/api/complaints/tickets/${ticketId}`);
}

/**
 * Get image by ID
 */
export function getImageUrl(imageId) {
  return `${API_BASE_URL}/api/complaints/images/${imageId}`;
}

/**
 * YOLO Detection - Detect image
 */
export async function detectImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/yolo/detect-image`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Detection failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * YOLO Detection - Detect video
 */
export async function detectVideo(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/yolo/detect-video`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Video detection failed: ${response.status}`);
  }

  return await response.json();
}

/**
 * Get YOLO annotated image URL
 */
export function getAnnotatedImageUrl(filename) {
  return `${API_BASE_URL}/api/yolo/annotated/${filename}`;
}

/**
 * Get YOLO original image URL
 */
export function getOriginalImageUrl(filename) {
  return `${API_BASE_URL}/api/yolo/original/${filename}`;
}

export default {
  uploadComplaints,
  getTickets,
  getTicketById,
  getImageUrl,
  detectImage,
  detectVideo,
  getAnnotatedImageUrl,
  getOriginalImageUrl,
};
