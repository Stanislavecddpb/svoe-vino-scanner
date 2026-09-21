import pg from 'pg'

let pool: pg.Pool | null = null

export function getPool(): pg.Pool {
  if (!pool) {
    pool = new pg.Pool({ connectionString: appConfig.databaseUrl, max: 5, connectionTimeoutMillis: 3000 })
    pool.on('error', () => {}) // idle client errors must not crash the server
  }
  return pool
}
