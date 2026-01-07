import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleLogout() {
    localStorage.clear();
    navigate("/");
  }

  return (
    <nav className="navbar">
      {/* LEFT: Logo + Brand */}
      <div className="nav-left">
        <div className="logo">MDMS</div>
        <span className="brand-text">Municipal Deviation Management System</span>
      </div>

      {/* HAMBURGER (mobile only) */}
      <button
        className="hamburger"
        onClick={() => setMenuOpen(!menuOpen)}
      >
        ☰
      </button>

      {/* RIGHT: Links + Logout */}
      <div className={`nav-right ${menuOpen ? "open" : ""}`}>
        <Link to="/home" onClick={() => setMenuOpen(false)}>Home</Link>
        <Link to="/map" onClick={() => setMenuOpen(false)}>Map</Link>
        <Link to="/complaints" onClick={() => setMenuOpen(false)}>Complaints</Link>
        <Link to="/tickets" onClick={() => setMenuOpen(false)}>TicketLog</Link>
        <Link to="/status" onClick={() => setMenuOpen(false)}>Status</Link>
        <Link to="/live" onClick={() => setMenuOpen(false)}>Live Monitoring</Link>

        <button
          className="logout-btn"
          onClick={() => {
            setMenuOpen(false);
            handleLogout();
          }}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
