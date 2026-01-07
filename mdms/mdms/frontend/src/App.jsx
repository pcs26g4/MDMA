import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import LoginSignup from "./components/pages/LoginSignup";
import HomePage from "./components/pages/HomePage";
import MapView from "./components/pages/MapView";
import AppLayout from "./components/Layout/AppLayout";
import ComplaintPage from "./components/pages/ComplaintPage";
import AnalysePage from "./components/pages/AnalysePage";
import TicketLog from "./components/pages/TicketLog";
// import FilterPage from "./components/Filter/FilterPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginSignup />} />

        <Route
          path="/home"
          element={
            <AppLayout>
              <HomePage />
            </AppLayout>
          }
        />

        <Route
          path="/map"
          element={
            <AppLayout>
              <MapView />
            </AppLayout>
          }
        />

        <Route
          path="/complaints"
          element={
            <AppLayout>
              <ComplaintPage />
            </AppLayout>
          }
        />

        <Route
          path="/analyse"
          element={
            <AppLayout>
              <AnalysePage />
            </AppLayout>
          }
        />

        {/* <Route
          path="/filter"
          element={
            <AppLayout>
              <FilterPage />
            </AppLayout>
          }
        /> */}

          <Route
          path="/tickets"
          element={
            <AppLayout>
              <TicketLog />
            </AppLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
