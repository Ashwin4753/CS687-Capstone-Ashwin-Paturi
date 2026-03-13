export default function ProductCard() {
  return (
    <article style={{ background:"#fff", padding:"16px", borderRadius:"12px", boxShadow:"0 2px 8px rgba(0,0,0,0.12)" }}>
      <h3 style={{ color:"#0f172a" }}>Sneaker</h3>
      <p style={{ color:"#64748b", marginBottom:"12px" }}>$79</p>
      <button style={{ background:"#f97316", color:"#ffffff", padding:"10px 16px", borderRadius:"999px" }}>
        Add to cart
      </button>
    </article>
  )
}
