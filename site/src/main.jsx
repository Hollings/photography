import React from "react";
import ReactDOM from "react-dom/client";
import App        from "./App";
import Management from "./Management";
import PhotoDetail from "./PhotoDetail";

const path = window.location.pathname;
let Root;
if (path.startsWith("/manage")) Root = Management;
else if (path.startsWith("/p/")) Root = PhotoDetail;
else Root = App;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode><Root /></React.StrictMode>
);
