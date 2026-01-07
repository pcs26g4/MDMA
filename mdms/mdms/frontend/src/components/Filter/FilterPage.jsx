import { useState } from "react";
import "./FilterPage.css";

function FilterPage() {
  /* ===============================
     FILTER OPTIONS
  =============================== */
  const categories = [
    "all",
    "garbage_overflow",
    "road_debris",
    "road_sand",
    "animal_carcass",
    "open_manhole",
    "pothole",
    "road_crack",
    "water_puddle",
    "street_hawker",
  ];

  const statuses = ["all", "accepted", "rejected", "in_progress"];

  /* ===============================
     FILTER STATE ONLY
  =============================== */
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedDate, setSelectedDate] = useState("");

  return (
    <div className="ticket-log">
      <h3 className="ticket-title">Ticket Filters</h3>

      {/* ===============================
          FILTER BAR
      =============================== */}
      <div className="filter-bar">
        <label htmlFor="">Distortion Type: </label>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat.replace("_", " ").toUpperCase()}
            </option>
          ))}
        </select>

        <label htmlFor="">Status: </label>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
        >
          {statuses.map((status) => (
            <option key={status} value={status}>
              {status.replace("_", " ").toUpperCase()}
            </option>
          ))}
        </select>
        <label htmlFor="">Date: </label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
        />
      </div>
    </div>
  );
}

export default FilterPage;
