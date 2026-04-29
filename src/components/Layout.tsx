import { useEffect, useRef } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import { useParkingContext } from "../hooks/useParkingState";

export default function Layout() {
  const { connected, sendCommand } = useParkingContext();
  const hasReset = useRef(false);

  useEffect(() => {
    if (connected && !hasReset.current) {
      sendCommand({ type: "export_and_reset" });
      hasReset.current = true;
    }
  }, [connected, sendCommand]);

  return (
    <>
      <Sidebar />
      <div className="ml-0 lg:ml-20 flex flex-col min-h-screen">
        <TopNav />
        <Outlet />
      </div>
    </>
  );
}