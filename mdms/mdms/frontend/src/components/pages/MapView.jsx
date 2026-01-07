import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import "../styles/MapView.css";
import { getTickets } from "../../services/api";
import L from "leaflet";

// Fix for default marker icon in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

/* -------------------- CONSTANTS -------------------- */
const DEFAULT_CENTER = [16.5062, 80.648]; // Vijayawada
const DEFAULT_ZOOM = 13;

/* -------------------- MAP RESET -------------------- */
function ResetMap({ reset }) {
  const map = useMap();

  useEffect(() => {
    if (reset) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }
  }, [reset, map]);

  return null;
}

/* -------------------- COMPLAINT MARKER -------------------- */
function ComplaintMarker({ position, label }) {
  const map = useMap();

  useEffect(() => {
    if (position) {
      map.setView(position, 16);
    }
  }, [position, map]);

  if (!position) return null;

  return (
    <Marker position={position}>
      <Popup>
        <strong>{label || "Complaint Location"}</strong>
        <br />
        Exact latitude & longitude
      </Popup>
    </Marker>
  );
}

/* -------------------- MAP VIEW -------------------- */
export default function MapView() {
  const location = useLocation();

  const [complaintPos, setComplaintPos] = useState(null);
  const [complaintLabel, setComplaintLabel] = useState("");
  const [allTickets, setAllTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  const isRedirected = Boolean(location.state?.lat && location.state?.lng);

  /* Fetch all tickets for map markers */
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await getTickets();
        const ticketsData = response.tickets || [];
        
        // Flatten tickets with sub_tickets and extract locations
        const ticketsWithLocations = [];
        ticketsData.forEach(ticket => {
          (ticket.sub_tickets || []).forEach(subTicket => {
            const lat = subTicket.latitude || ticket.latitude;
            const lng = subTicket.longitude || ticket.longitude;
            
            if (lat && lng) {
              ticketsWithLocations.push({
                ...subTicket,
                ticket_id: ticket.ticket_id,
                latitude: lat,
                longitude: lng,
              });
            }
          });
        });
        
        setAllTickets(ticketsWithLocations);
      } catch (error) {
        console.error("Failed to fetch tickets for map:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, []);

  /* Handle navigation state */
  useEffect(() => {
    if (isRedirected) {
      setComplaintPos([location.state.lat, location.state.lng]);
      setComplaintLabel(location.state.label || "Complaint Location");
    } else {
      // Initial load OR refresh
      setComplaintPos(null);
      setComplaintLabel("");
    }
  }, [location.state, isRedirected]);

  return (
    <div className="map-section">
      <div className="map-header">
        <h3>Live Detection Map</h3>
      </div>

      <div className="map-shell">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          className="map"
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          {/* Reset map on initial load / refresh */}
          <ResetMap reset={!isRedirected} />

          {/* Show marker ONLY when redirected */}
          {isRedirected && (
            <ComplaintMarker position={complaintPos} label={complaintLabel} />
          )}

          {/* Show all ticket markers */}
          {!loading && allTickets.map((ticket) => {
            if (!ticket.latitude || !ticket.longitude) return null;
            
            return (
              <Marker 
                key={ticket.sub_id || ticket.ticket_id} 
                position={[ticket.latitude, ticket.longitude]}
              >
                <Popup>
                  <strong>Ticket: {ticket.ticket_id}</strong>
                  <br />
                  <strong>Sub ID: {ticket.sub_id}</strong>
                  <br />
                  Issue: {ticket.issue_type || "-"}
                  <br />
                  Authority: {ticket.authority || "-"}
                  <br />
                  Status: {ticket.status || "-"}
                  <br />
                  Location: {ticket.latitude.toFixed(6)}, {ticket.longitude.toFixed(6)}
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
