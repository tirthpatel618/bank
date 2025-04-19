import { Pool } from 'pg';
import dotenv from 'dotenv';

/*
old db config for localhost
dotenv.config();

const pool = new Pool({
  // Change this based on prod env too 
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD
});
*/
dotenv.config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});
export default pool;
