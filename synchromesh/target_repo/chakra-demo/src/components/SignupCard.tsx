import React from "react";

export function SignupCard() {
  return (
    <div style={{ background: 'var(--color.white)', borderRadius: 'var(--spacing.3)', padding: '20px', width: '320px' }}>
      <h2 style={{ color: '#1a202c', marginBottom: 'var(--spacing.2)' }}>Create account</h2>
      <p style={{ color: '#4a5568', marginBottom: 'var(--spacing.3)' }}>Start your free trial.</p>
      <button style={{ background: '#805ad5', color: 'var(--color.white)', padding: '10px 14px', borderRadius: 'var(--spacing.2)' }}>
        Sign up
      </button>
    </div>
  );
}
