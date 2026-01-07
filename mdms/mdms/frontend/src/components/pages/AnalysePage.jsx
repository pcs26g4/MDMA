import { useEffect, useMemo, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/AnalysePage.css";

function AnalysePage() {
  const navigate = useNavigate();
  const location = useLocation();

  // Files received from ComplaintPage (after backend upload)
  const uploadedFiles = location.state?.uploadedFiles || [];
  const uploadResponse = location.state?.uploadResponse || null;

  const [showPopup, setShowPopup] = useState(false);

  // ===============================
  // CREATE PREVIEW URLs SAFELY
  // ===============================
  const previewFiles = useMemo(() => {
    return uploadedFiles.map((item) => ({
      ...item,
      previewUrl: item.previewUrl || (item.file ? URL.createObjectURL(item.file) : null),
    }));
  }, [uploadedFiles]);

  // ===============================
  // CLEANUP BLOB URLS
  // ===============================
  useEffect(() => {
    return () => {
      previewFiles.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl);
        }
      });
    };
  }, [previewFiles]);

  // ===============================
  // HANDLERS
  // ===============================
  const handleSubmit = (e) => {
    e.preventDefault();
    setShowPopup(true);
  };

  const handleOkClick = () => {
    setShowPopup(false);
    // After successful submission, go to Ticket Log so user can see updated tickets
    navigate("/tickets");
  };

  const handleLocationClick = (lat, lng) => {
    if (
      lat === undefined ||
      lng === undefined ||
      Number.isNaN(Number(lat)) ||
      Number.isNaN(Number(lng))
    ) {
      alert("Location not available for this item.");
      return;
    }

    navigate("/map", {
      state: {
        lat: Number(lat),
        lng: Number(lng),
      },
    });
  };

  // ===============================
  // UI
  // ===============================
  return (
    <div className="analyze-container">
      <h2 className="analyze-title">Complaint</h2>

      <p className="analyze-subtitle">
        Images and videos will be analyzed using a Deep Learning model.
      </p>

      {previewFiles.length === 0 ? (
        <p style={{ color: "white" }}>
          No images or videos received from complaint page.
        </p>
      ) : (
        <div className="table-wrapper">
          <table className="analyze-table">
            <thead>
              <tr>
                <th>Preview</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {previewFiles.map((file, index) => {
                const distortionCount = file.distortionCount ?? 1;
                const shouldShowSubId =
                  previewFiles.length > 1 || distortionCount > 1;

                return (
                  <tr key={file.id || index}>
                    <td>
                      {file.previewUrl ? (
                        file.type === "image" ? (
                          <img
                            src={file.previewUrl}
                            alt="preview"
                            className="preview-img"
                          />
                        ) : (
                          <video
                            src={file.previewUrl}
                            controls
                            className="preview-video"
                          />
                        )
                      ) : (
                        "-"
                      )}
                    </td>

                    <td>
                      <div className="details-box">
                        <div>
                          <strong>Issue Type: </strong> {file.issue_type ?? "-"}
                        </div>

                        <div>
                          <strong>Authority: </strong> {file.authority ?? "-"}
                        </div>

                        <div>
                          <strong>Status: </strong> {file.status ?? "-"}
                        </div>

                        <div>
                          <strong>Ticket ID: </strong> {file.ticket_id ?? "-"}
                        </div>

                        {shouldShowSubId && (
                          <div>
                            <strong>Sub ID: </strong>{" "}
                            {file.sub_id ?? `SUB-${index + 1}`}
                          </div>
                        )}

                        <div>
                          <strong>Latitude: </strong> {file.latitude ?? "-"}
                        </div>

                        <div>
                          <strong>Longitude: </strong> {file.longitude ?? "-"}
                        </div>

                        <div>
                          <strong>Media Count: </strong> {file.media_count ?? 0}
                        </div>

                        {file.rejected_count > 0 && (
                          <div style={{ color: '#ef4444' }}>
                            <strong>Rejected: </strong> {file.rejected_count} duplicate(s)
                          </div>
                        )}

                        <div>
                          <strong>Location: </strong>{" "}
                          <span
                            className="location-link"
                            onClick={() =>
                              handleLocationClick(file.latitude, file.longitude)
                            }
                          >
                             View on Map
                          </span>
                        </div>

                        <div>
                          <strong>File Type: </strong>{" "}
                          {file.type?.toUpperCase() ?? "IMAGE"}
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="submit-section">
        <button className="submit-btn" onClick={handleSubmit}>
          Submit
        </button>
      </div>

      {showPopup && (
        <div className="popup-overlay">
          <div className="popup-card">
            <h3>✅ Submitted Successfully</h3>

            {uploadResponse?.message && (
              <p style={{ color: '#ef4444', marginBottom: '12px' }}>
                {uploadResponse.message}
              </p>
            )}

            {previewFiles.length > 0 && (
              <p>
                <strong>Ticket ID:</strong>{" "}
                {previewFiles[0]?.ticket_id || "-"}
              </p>
            )}

            {(previewFiles.length > 1 ||
              previewFiles.some((f) => f.sub_id)) && (
              <>
                <p>
                  <strong>Sub Tickets:</strong>
                </p>
                <ul>
                  {previewFiles.map((file, index) => (
                    <li key={index}>
                      {file.sub_id || `SUB-${index + 1}`} - {file.issue_type}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <button className="popup-btn" onClick={handleOkClick}>
              OK
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AnalysePage;
