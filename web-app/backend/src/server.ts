import express from 'express';
import cors from 'cors';
import pool from './db';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

app.get('/api/quotes', async (req, res) => {
  try {
    console.log("DB URL:", process.env.DATABASE_URL);
    const result = await pool.query('SELECT * FROM vachanamrut_quotes ORDER BY id DESC');
    console.log("Quotes:", result.rows);
    res.json(result.rows);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/api/topics', async (req, res) => {
  try {
    const result = await pool.query('SELECT DISTINCT topic FROM vachanamrut_quotes');
    const topics = result.rows.map((row: any) => row.topic);

    res.json(topics);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
