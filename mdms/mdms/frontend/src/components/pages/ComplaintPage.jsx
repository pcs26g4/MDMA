// import { useNavigate } from "react-router-dom";

// export default function ComplaintPage() {
//   const navigate = useNavigate();

//   // Example complaint coordinates
//   const latitude = 16.5062;
//   const longitude = 80.648;
//   const locationLabel = "Vijayawada";

//   function handleLocationClick() {
//     navigate("/map", {
//       state: {
//         lat: latitude,
//         lng: longitude,
//         label: locationLabel,
//       },
//     });
//   }

//   return (
//     <div>
//       <h2>Complaint Details</h2>

//       <p><strong>Latitude:</strong> {latitude}</p>
//       <p><strong>Longitude:</strong> {longitude}</p>

//       <p>
//         <strong>Location:</strong>{" "}
//         <span
//           onClick={handleLocationClick}
//           style={{
//             color: "#2563eb",
//             cursor: "pointer",
//             textDecoration: "underline",
//           }}
//         >
//           {locationLabel} (View on Map)
//         </span>
//       </p>
//     </div>
//   );
// }

import { useRef, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/ComplaintPage.css";
import { uploadComplaints } from "../../services/api";
// import cityBg from "../../assets/images/mdms-complaint.png";

function ComplaintPage() {
  const navigate = useNavigate();

  /* ===================== REFS ===================== */
  const imageGalleryRef = useRef(null);
  const videoGalleryRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);

  /* ===================== STATE ===================== */
  const [images, setImages] = useState([]);
  const [videos, setVideos] = useState([]);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [location, setLocation] = useState({ lat: null, lng: null, error: null });

  /* ===================== CAMERA ===================== */
  const openCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      setStream(mediaStream);
      setCameraOpen(true);
    } catch {
      alert("Camera permission denied");
    }
  };

  useEffect(() => {
    if (cameraOpen && stream && videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [cameraOpen, stream]);

  // Get user geolocation once
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocation((prev) => ({ ...prev, error: "Geolocation not supported" }));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          error: null,
        });
      },
      (err) => {
        setLocation((prev) => ({ ...prev, error: err.message || "Location unavailable" }));
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  }, []);

  const captureImage = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    // Convert canvas to blob and create File object
    canvas.toBlob((blob) => {
      const file = new File([blob], `camera-${Date.now()}.png`, { type: 'image/png' });
      setImages((prev) => [
        ...prev,
        { 
          id: crypto.randomUUID(), 
          url: canvas.toDataURL("image/png"),
          file: file,
          lat: location.lat,
          lng: location.lng,
        },
      ]);
    }, 'image/png');
  };

  const startRecording = () => {
    recordedChunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(recordedChunksRef.current, {
        type: "video/webm",
      });
      const file = new File([blob], `recording-${Date.now()}.webm`, { type: 'video/webm' });
      setVideos((prev) => [
        ...prev,
        { 
          id: crypto.randomUUID(), 
          url: URL.createObjectURL(blob),
          file: file,
          lat: location.lat,
          lng: location.lng,
        },
      ]);
    };

    recorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const closeCamera = () => {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    setCameraOpen(false);
    setStream(null);
    setIsRecording(false);
  };

  /* ===================== UPLOADS ===================== */
  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    setImages((prev) => [
      ...prev,
      ...files.map((f) => ({
        id: crypto.randomUUID(),
        url: URL.createObjectURL(f),
        file: f, // Store the actual File object
        lat: location.lat,
        lng: location.lng,
      })),
    ]);
    e.target.value = "";
  };

  const handleVideoUpload = (e) => {
    const files = Array.from(e.target.files);
    setVideos((prev) => [
      ...prev,
      ...files.map((f) => ({
        id: crypto.randomUUID(),
        url: URL.createObjectURL(f),
        file: f, // Store the actual File object
        lat: location.lat,
        lng: location.lng,
      })),
    ]);
    e.target.value = "";
  };

  const removeImage = (id) =>
    setImages((prev) => prev.filter((i) => i.id !== id));
  const removeVideo = (id) =>
    setVideos((prev) => prev.filter((v) => v.id !== id));

  const resetFiles = () => {
    setImages([]);
    setVideos([]);
  };

  /* ===================== ANALYZE ===================== */
  const handleAnalyze = async () => {
    if (images.length === 0 && videos.length === 0) {
      alert("Please add at least one image or video.");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      // Convert blob URLs to File objects
      const filesToUpload = [];

      // Convert images
      for (const img of images) {
        if (img.file) {
          filesToUpload.push(img.file);
        } else if (img.url && img.url.startsWith('blob:')) {
          // Convert blob URL to File
          const response = await fetch(img.url);
          const blob = await response.blob();
          const file = new File([blob], `image-${img.id}.jpg`, { type: blob.type });
          filesToUpload.push(file);
        } else if (img.url && img.url.startsWith('data:')) {
          // Convert data URL to File
          const response = await fetch(img.url);
          const blob = await response.blob();
          const file = new File([blob], `image-${img.id}.jpg`, { type: blob.type });
          filesToUpload.push(file);
        }
      }

      // Convert videos
      for (const vid of videos) {
        if (vid.file) {
          filesToUpload.push(vid.file);
        } else if (vid.url && vid.url.startsWith('blob:')) {
          const response = await fetch(vid.url);
          const blob = await response.blob();
          const file = new File([blob], `video-${vid.id}.webm`, { type: blob.type });
          filesToUpload.push(file);
        }
      }

      if (filesToUpload.length === 0) {
        throw new Error("No valid files to upload");
      }

      // Upload to backend
      const response = await uploadComplaints(filesToUpload);

      // If backend detected duplicates, show popup/alert
      if (response?.duplicates_found && response.duplicates_found > 0) {
        alert(
          response.message ||
            `Some images were already registered. Duplicates: ${response.duplicates_found}`
        );
      }

      // Process response and prepare data for AnalysePage
      const uploadedFiles = [];
      
      if (response.tickets_created && response.tickets_created.length > 0) {
        for (const ticket of response.tickets_created) {
          for (const subTicket of ticket.sub_tickets || []) {
            // Find corresponding image/video
            const mediaIndex = uploadedFiles.length;
            const originalMedia = [...images, ...videos][mediaIndex];
            
            uploadedFiles.push({
              id: originalMedia?.id || `media-${mediaIndex}`,
              previewUrl: originalMedia?.url,
              type: subTicket.issue_type === 'video' ? 'video' : 'image',
              ticket_id: ticket.ticket_id,
              sub_id: subTicket.sub_id,
              issue_type: subTicket.issue_type,
              authority: subTicket.authority,
              status: subTicket.status,
              latitude: subTicket.latitude || ticket.latitude || originalMedia?.lat,
              longitude: subTicket.longitude || ticket.longitude || originalMedia?.lng,
              media_count: subTicket.media_count,
              rejected_count: subTicket.rejected_count,
            });
          }
        }
      }

      // Navigate to analyse page with results
      navigate("/analyse", { 
        state: { 
          uploadedFiles,
          uploadResponse: response,
        } 
      });
    } catch (error) {
      console.error("Upload error:", error);
      setUploadError(error.message || "Failed to upload complaints. Please try again.");
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    return () => closeCamera();
  }, []);

  /* ===================== UI ===================== */
  return (
    <div className="complaint-container">
      {/* HEADER */}
      <div className="complaint-header">
        <h2>Municipal Deviation Registration</h2>
        <p>
          Submit visual evidence for civic issues such as road damage, drainage
          blockage, waste accumulation, or public infrastructure faults.
        </p>
      </div>

      {/* UPLOAD SECTION */}
      <div className="card">
        <h3>Add Evidence</h3>
        <div className="upload-buttons">
          <button onClick={() => imageGalleryRef.current.click()}>
            📁 Upload Images
          </button>
          <button onClick={() => videoGalleryRef.current.click()}>
            🎥 Upload Videos
          </button>
          <button onClick={openCamera}>📷 Capture Using Camera</button>
        </div>

        <input
          ref={imageGalleryRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={handleImageUpload}
        />
        <input
          ref={videoGalleryRef}
          type="file"
          accept="video/*"
          multiple
          hidden
          onChange={handleVideoUpload}
        />
      </div>

      {/* CAMERA */}
      {cameraOpen && (
        <div className="card camera-box">
          <video ref={videoRef} autoPlay playsInline />
          <div className="camera-actions">
            <button onClick={captureImage}>📸 Capture Photo</button>
            {!isRecording ? (
              <button onClick={startRecording}>⏺ Start Recording</button>
            ) : (
              <button onClick={stopRecording}>⏹ Stop Recording</button>
            )}
            <button onClick={closeCamera}>❌ Close Camera</button>
          </div>
        </div>
      )}

      <canvas ref={canvasRef} hidden />

      {/* PREVIEW */}
      {(images.length > 0 || videos.length > 0) && (
        <div className="card preview">
          <h4>Review Evidence</h4>

          {images.length > 0 && (
            <>
              <p>Images</p>
              <div className="preview-grid">
                {images.map((img) => (
                  <div key={img.id} className="preview-item">
                    <img src={img.url} alt="evidence" />
                    <button onClick={() => removeImage(img.id)}>✖</button>
                  </div>
                ))}
              </div>
            </>
          )}

          {videos.length > 0 && (
            <>
              <p style={{ marginTop: "16px" }}>Videos</p>
              <div className="preview-grid">
                {videos.map((vid) => (
                  <div key={vid.id} className="preview-item">
                    <video src={vid.url} controls className="preview-video" />
                    <button onClick={() => removeVideo(vid.id)}>✖</button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ACTIONS */}
      {(images.length > 0 || videos.length > 0) && (
        <div className="card">
          {uploadError && (
            <div style={{ 
              padding: '12px', 
              marginBottom: '16px', 
              background: '#fee2e2', 
              color: '#dc2626', 
              borderRadius: '6px' 
            }}>
              {uploadError}
            </div>
          )}
          <div className="action-buttons">
            <button 
              className="retry-btn" 
              onClick={resetFiles}
              disabled={uploading}
            >
              Clear Evidence
            </button>
            <button 
              className="analyze-btn" 
              onClick={handleAnalyze}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Proceed to Analysis"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ComplaintPage;
