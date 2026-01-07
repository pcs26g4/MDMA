import { useState } from "react";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

export default function InteractivePie() {
  const stats = {
    total: 120,
    resolved: 70,
    working: 30,
  };

  const openCount = stats.total - stats.resolved - stats.working;

  const [activeIndex, setActiveIndex] = useState(null);

  const data = {
    labels: ["Resolved", "In Progress", "Open"],
    datasets: [
      {
        data: [stats.resolved, stats.working, openCount],
        backgroundColor: ["#22c55e", "#f59e0b", "#ef4444"],
        hoverBackgroundColor: ["#16a34a", "#d97706", "#dc2626"],
        offset: (ctx) => (ctx.dataIndex === activeIndex ? 12 : 0), // 🔥 slice pops out
        borderWidth: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.label}: ${ctx.raw} complaints`,
        },
      },
    },
    onClick: (_, elements) => {
      if (!elements.length) return;
      setActiveIndex(elements[0].index);
    },
    onHover: (_, elements) => {
      if (elements.length) {
        setActiveIndex(elements[0].index);
      }
    },
  };

  const centerLabel =
    activeIndex === 0
      ? "Resolved"
      : activeIndex === 1
      ? "In Progress"
      : activeIndex === 2
      ? "Open"
      : "Total";

  const centerValue =
    activeIndex === 0
      ? stats.resolved
      : activeIndex === 1
      ? stats.working
      : activeIndex === 2
      ? openCount
      : stats.total;

  return (
    <div className="pie-box">
      <div className="pie-chart">
        <Pie data={data} options={options} />
        <div className="pie-center">
          <p>{centerLabel}</p>
          <h2>{centerValue}</h2>
        </div>
      </div>

      <div className="pie-legend">
        {["Resolved", "In Progress", "Open"].map((label, i) => (
          <span
            key={label}
            className={activeIndex === i ? "active" : ""}
            onClick={() => setActiveIndex(i)}
          >
            <i className={`dot ${label.toLowerCase().replace(" ", "")}`}></i>
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
