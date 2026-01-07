import "../styles/HomePage.css"
import { useEffect, useState } from "react";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { getTickets } from "../../services/api";

ChartJS.register(ArcElement, Tooltip, Legend);

export default function HomePage() {
  /* ================= API STATE ================= */
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, resolved: 0, working: 0, open: 0 });

  /* ================= FETCH TICKETS ================= */
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await getTickets();
        const ticketsData = response.tickets || [];
        setTickets(ticketsData);
        
        // Calculate stats from actual data
        const total = ticketsData.length;
        const resolved = ticketsData.filter(t => t.status === 'resolved' || t.status === 'closed').length;
        const working = ticketsData.filter(t => t.status === 'in_progress' || t.status === 'working').length;
        const open = total - resolved - working;
        
        setStats({ total, resolved, working, open });
      } catch (err) {
        console.error("Failed to fetch tickets", err);
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, []);

  /* ================= RECENT ACTIVITY LOGIC ================= */
  const recentTickets = tickets
    .flatMap(ticket => 
      (ticket.sub_tickets || []).map(subTicket => ({
        ...subTicket,
        ticket_id: ticket.ticket_id,
        created_at: subTicket.created_at || ticket.created_at,
      }))
    )
    .sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
      const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
      return dateB - dateA;
    })
    .slice(0, 3);

  /* ================= DASHBOARD STATS ================= */
  const openCount = stats.open;

  const pieData = {
    labels: ["Resolved", "In Progress", "Open"],
    datasets: [
      {
        data: [stats.resolved, stats.working, openCount],
        backgroundColor: ["#22c55e", "#f59e0b", "#ef4444"],
        hoverOffset: 18,
        borderWidth: 0,
      },
    ],
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
  };

  return (
    <div className="home-container">
      {/* ================= BACKGROUND VIDEO ================= */}
      {/* <video className="bg-video" autoPlay muted loop playsInline>
        <source src="/mdms-bgg.mp4" type="video/mp4" />
      </video> */}

      <div className="home-content">
        {/* ================= SNAPSHOT BAR ================= */}
        <div className="snapshot-bar">
          <div className="snapshot-item">
            <span className="label">Today: </span>
            <span className="value">18</span>
          </div>

          <div className="divider" />

          <div className="snapshot-item new">
            <span className="label">New: </span>
            <span className="value">12</span>
          </div>

          <div className="divider" />

          <div className="snapshot-item resolved">
            <span className="label">Resolved: </span>
            <span className="value">7</span>
          </div>

          <div className="divider" />

          <div className="snapshot-item open">
            <span className="label">Open: </span>
            <span className="value">5</span>
          </div>
        </div>

        {/* ================= GRID 1 ================= */}
        <div className="grid-2">
          <div className="stats-grid">
            <div className="stat-card total">
              <p>Total Complaints</p>
              <h2>{stats.total}</h2>
            </div>
            <div className="stat-card resolved">
              <p>Resolved</p>
              <h2>{stats.resolved}</h2>
            </div>
            <div className="stat-card working">
              <p>In Progress</p>
              <h2>{stats.working}</h2>
            </div>
            <div className="stat-card open">
              <p>Open</p>
              <h2>{openCount}</h2>
            </div>
          </div>

          <div className="pie-card">
            <h3>Complaint Status</h3>
            <div className="pie-box">
              <Pie data={pieData} options={pieOptions} />
            </div>
          </div>
        </div>

        {/* ================= GRID 2 ================= */}
        <div className="grid-2">
          <div className="sla-card">
            <h3>SLA Health</h3>
            <div className="sla-row green">
              On Time <span>82%</span>
            </div>
            <div className="sla-row amber">
              At Risk <span>12%</span>
            </div>
            <div className="sla-row red">
              Breached <span>6%</span>
            </div>
          </div>

          <div className="category-card">
            <h3>Top Categories</h3>
            <ul>
              <li>Potholes</li>
              <li>Garbage Overflow</li>
              <li>Open Manholes</li>
            </ul>
          </div>
        </div>

        {/* ================= RECENT ACTIVITY ================= */}
        <div className="activity-card">
          <h3>Recent Activity</h3>

          {loading && <p>Loading recent activity...</p>}

          {!loading && recentTickets.length === 0 && (
            <p>No recent activity</p>
          )}

          {!loading &&
            recentTickets.map((subTicket) => (
              <div
                key={subTicket.sub_id}
                className="activity-item"
              >
                <span className="activity-icon">
                  {subTicket.issue_type === "pathholes" && "🛣️"}
                  {subTicket.issue_type === "garbage" && "🗑️"}
                  {subTicket.issue_type === "streetdebris" && "🚧"}
                  {!subTicket.issue_type && "📋"}
                </span>

                <div className="activity-text">
                  <strong>
                    {subTicket.issue_type
                      ? subTicket.issue_type.replace("_", " ").toUpperCase()
                      : "COMPLAINT"}
                  </strong>

                  <span className="activity-meta">
                    Ticket: {subTicket.ticket_id}
                  </span>

                  <span className="activity-meta">
                    {subTicket.created_at 
                      ? new Date(subTicket.created_at).toLocaleString()
                      : "Recently"}
                  </span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
