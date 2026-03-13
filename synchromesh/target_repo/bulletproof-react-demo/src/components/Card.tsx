import React from "react";

const cardStyle = {
  background: "rgb(255,255,255)",
  padding: "16px",
  margin: "12px",
  borderRadius: "8px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
};

export function Card() {
  return <div style={cardStyle}>Profile Summary</div>;
}
