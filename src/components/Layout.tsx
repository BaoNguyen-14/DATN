import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";
import Footer from "./Footer";

export default function Layout() {
  return (
    <>
      <Sidebar />
      <div className="ml-0 lg:ml-20 flex flex-col min-h-screen">
        <TopNav />
        <Outlet />
        <Footer />
      </div>
    </>
  );
}