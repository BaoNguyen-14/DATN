import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ParkingProvider } from "./hooks/useParkingState";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ParkingMap from "./pages/ParkingMap";
import History from "./pages/History";
import Settings from "./pages/Settings";

function App() {
  return (
    <ParkingProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="parking-map" element={<ParkingMap />} />
            <Route path="history" element={<History />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ParkingProvider>
  );
}

export default App;