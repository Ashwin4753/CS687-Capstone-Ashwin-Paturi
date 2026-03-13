import React from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

export default function Dashboard() {
  return (
    <section style={{ padding: "24px", background: "#f8fafc" }}>
      <h1 style={{ color: "#1f2937", marginBottom: "12px" }}>Dashboard</h1>
      <Card />
      <Button />
    </section>
  );
}
