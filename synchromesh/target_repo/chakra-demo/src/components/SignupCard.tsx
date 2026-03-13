import React from "react";

export function SignupCard() {
  return (
    <div style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', width: '320px' }}>
      <h2 style={{ color: '#1a202c', marginBottom: '8px' }}>Create account</h2>
      <p style={{ color: '#4a5568', marginBottom: '12px' }}>Start your free trial.</p>
      <button style={{ background: '#805ad5', color: '#ffffff', padding: '10px 14px', borderRadius: '8px' }}>
        Sign up
      </button>
    </div>
  );
}
