import { useState, useEffect } from "react";
import "../styles/TicketLog.css";
import { getTickets, getImageUrl } from "../../services/api";

function TicketLog() {
  /* ===============================
     CONSTANTS
  =============================== */
  const ITEMS_PER_PAGE = 10;

  /* ===============================
     FILTER OPTIONS
  =============================== */
  const distortions = [
    "all",
    "pathholes",
    "garbage",
    "streetdebris",
  ];

  const statuses = ["all", "open", "in_progress", "resolved", "closed"];

  /* ===============================
     STATE
  =============================== */
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  /* ===============================
     FETCH TICKETS
  =============================== */
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await getTickets();
        // Flatten tickets with sub_tickets
        const allSubTickets = [];
        (response.tickets || []).forEach(ticket => {
          (ticket.sub_tickets || []).forEach(subTicket => {
            allSubTickets.push({
              ...subTicket,
              ticket_id: ticket.ticket_id,
              ticket_latitude: ticket.latitude,
              ticket_longitude: ticket.longitude,
            });
          });
        });
        setTickets(allSubTickets);
      } catch (error) {
        console.error("Failed to fetch tickets:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, []);

  /* ===============================
     FILTER STATE
  =============================== */
  const [selectedDistortion, setSelectedDistortion] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedDate, setSelectedDate] = useState("");

  /* ===============================
     FILTER VISIBILITY STATE
  =============================== */
  const [showFilters, setShowFilters] = useState(false);

  /* ===============================
     PAGINATION STATE
  =============================== */
  const [currentPage, setCurrentPage] = useState(1);

  /* ===============================
     FILTER + SORT LOGIC
  =============================== */
  const filteredTickets = tickets
    .filter((ticket) => {
      const distortionMatch =
        selectedDistortion === "all" ||
        ticket.issue_type === selectedDistortion;

      const statusMatch =
        selectedStatus === "all" || ticket.status === selectedStatus;

      const dateMatch =
        selectedDate === "" || 
        (ticket.created_at && ticket.created_at.startsWith(selectedDate));

      return distortionMatch && statusMatch && dateMatch;
    })
    .sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
      const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
      return dateB - dateA;
    });

  /* ===============================
     PAGINATION LOGIC
  =============================== */
  const totalPages = Math.ceil(filteredTickets.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedTickets = filteredTickets.slice(startIndex, endIndex);

  const handleFilterChange = (setter) => (value) => {
    setter(value);
    setCurrentPage(1);
  };

  return (
    <div className="ticket-log">
      {/* ===============================
          FILTER BUTTON
      =============================== */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: "12px",
        }}
      >
        <button
          onClick={() => setShowFilters((prev) => !prev)}
          style={{
            background: "#ff5a4e",
            color: "#ffffff",
            border: "none",
            padding: "10px 18px",
            borderRadius: "6px",
            fontWeight: "700",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          🔽 FILTER
        </button>
      </div>

      {/* ===============================
          FILTER BAR (TOGGLE)
      =============================== */}
      {showFilters && (
        <div className="filter-bar">
          <div className="filter-group">
            <label className="filter-label">Distortion Type</label>
            <select
              value={selectedDistortion}
              onChange={(e) =>
                handleFilterChange(setSelectedDistortion)(e.target.value)
              }
            >
              {distortions.map((dist) => (
                <option key={dist} value={dist}>
                  {dist.replace("_", " ").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Status</label>
            <select
              value={selectedStatus}
              onChange={(e) =>
                handleFilterChange(setSelectedStatus)(e.target.value)
              }
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status.replace("_", " ").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Date</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) =>
                handleFilterChange(setSelectedDate)(e.target.value)
              }
            />
          </div>
        </div>
      )}

      {/* ===============================
          TABLE
      =============================== */}
      <div className="table-wrapper">
        <table className="ticket-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Preview</th>
              <th>Sub ID</th>
              <th>Issue Type</th>
              <th>Date & Time</th>
              <th>Location</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="no-data">
                  Loading...
                </td>
              </tr>
            ) : paginatedTickets.length === 0 ? (
              <tr>
                <td colSpan="7" className="no-data">
                  No records found
                </td>
              </tr>
            ) : (
              paginatedTickets.map((ticket, index) => {
                const lat = ticket.latitude || ticket.ticket_latitude;
                const lng = ticket.longitude || ticket.ticket_longitude;
                const imageId = ticket.image_id;
                
                return (
                  <tr key={ticket.sub_id || index}>
                    <td>{startIndex + index + 1}</td>

                    <td className="preview-cell">
                      {imageId ? (
                        <img
                          src={getImageUrl(imageId)}
                          alt="Complaint"
                          className="preview-img"
                          onError={(e) => {
                            e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23ddd" width="100" height="100"/%3E%3Ctext fill="%23999" x="50%" y="50%" text-anchor="middle" dy=".3em"%3ENo Image%3C/text%3E%3C/svg%3E';
                          }}
                        />
                      ) : (
                        <div className="preview-img" style={{ 
                          background: '#ddd', 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          color: '#999'
                        }}>
                          No Image
                        </div>
                      )}
                    </td>

                    <td>{ticket.sub_id || ticket.ticket_id}</td>
                    <td>{ticket.issue_type || "-"}</td>

                    <td>
                      {ticket.created_at 
                        ? new Date(ticket.created_at).toLocaleDateString()
                        : "-"}
                      <br />
                      <span style={{ fontSize: "12px", opacity: 0.7 }}>
                        {ticket.created_at 
                          ? new Date(ticket.created_at).toLocaleTimeString()
                          : "-"}
                      </span>
                    </td>

                    <td>
                    {lat && lng ? (
                      <a
                        href={`https://www.google.com/maps?q=${lat},${lng}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="location-link"
                      >
                        {lat.toFixed(6)}, {lng.toFixed(6)}
                      </a>
                    ) : (
                      <span className="location-link" style={{ opacity: 0.7 }}>
                        Location not available
                      </span>
                    )}
                    </td>

                    <td>{ticket.status || "-"}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ===============================
          PAGINATION
      =============================== */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage((p) => p - 1)}
          >
            Prev
          </button>

          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i + 1}
              className={currentPage === i + 1 ? "active" : ""}
              onClick={() => setCurrentPage(i + 1)}
            >
              {i + 1}
            </button>
          ))}

          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default TicketLog;