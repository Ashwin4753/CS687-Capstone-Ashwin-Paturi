import Navbar from '../components/Navbar'
import StatTile from '../components/StatTile'

export default function Home() {
  return (
    <div style={{ background: '#f1f5f9', minHeight: '100vh', padding: '24px' }}>
      <Navbar />
      <div style={{ marginTop: '16px' }}>
        <StatTile />
      </div>
    </div>
  )
}
