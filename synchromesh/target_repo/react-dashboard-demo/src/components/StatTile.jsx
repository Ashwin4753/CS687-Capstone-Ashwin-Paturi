const tileStyle = {
  background: 'var(--color.white)',
  borderRadius: 'var(--spacing.2)',
  padding: 'var(--spacing.4)',
  margin: 'var(--spacing.3)',
  border: '1px solid #e2e8f0',
}

export default function StatTile() {
  return <div style={tileStyle}>Revenue: $18,400</div>
}
