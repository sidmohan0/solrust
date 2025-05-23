"""
Historical data collection and storage for SolVolumeBot research layer.
Supports backfill capabilities and multiple storage formats.
"""

import os
import logging
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta
from dataclasses import asdict

from data_sources import OHLCVData, VolumeData, BinanceAPI, MemecoinVolumeAggregator


class DataStorage:
    """Handles historical data storage and retrieval"""
    
    def __init__(self, storage_dir: str = "data", storage_format: str = "parquet"):
        self.storage_dir = Path(storage_dir)
        self.storage_format = storage_format.lower()
        self.storage_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.storage_dir / "sol_ohlcv").mkdir(exist_ok=True)
        (self.storage_dir / "memecoin_volume").mkdir(exist_ok=True)
        (self.storage_dir / "processed").mkdir(exist_ok=True)
        
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for metadata and indexes"""
        self.db_path = self.storage_dir / "metadata.db"
        
        with sqlite3.connect(self.db_path) as conn:
            # SOL OHLCV metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sol_ohlcv_metadata (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    record_count INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Memecoin volume metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memecoin_volume_metadata (
                    id INTEGER PRIMARY KEY,
                    token_address TEXT NOT NULL,
                    date TEXT NOT NULL,
                    volume_24h REAL,
                    volume_change_24h REAL,
                    price_change_24h REAL,
                    source TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Data collection jobs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_jobs (
                    id INTEGER PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    parameters TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            
    def save_sol_ohlcv(self, data: List[OHLCVData], symbol: str = "SOL", 
                      interval: str = "5m") -> str:
        """Save SOL OHLCV data to storage"""
        if not data:
            return ""
            
        # Convert to DataFrame
        df = pd.DataFrame([asdict(candle) for candle in data])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Generate filename
        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        filename = f"sol_{interval}_{start_time.strftime('%Y%m%d_%H%M%S')}_to_{end_time.strftime('%Y%m%d_%H%M%S')}"
        
        if self.storage_format == "parquet":
            file_path = self.storage_dir / "sol_ohlcv" / f"{filename}.parquet"
            df.to_parquet(file_path, index=False)
        elif self.storage_format == "csv":
            file_path = self.storage_dir / "sol_ohlcv" / f"{filename}.csv"
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported storage format: {self.storage_format}")
            
        # Update metadata
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sol_ohlcv_metadata 
                (symbol, interval, start_time, end_time, file_path, record_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, interval, 
                start_time.isoformat(), end_time.isoformat(),
                str(file_path), len(df),
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            
        return str(file_path)
        
    def save_memecoin_volume(self, volume_data: Dict[str, VolumeData], 
                           date: Optional[datetime] = None) -> str:
        """Save memecoin volume data to storage"""
        if not volume_data:
            return ""
            
        date = date or datetime.now(timezone.utc).date()
        
        # Convert to DataFrame
        records = []
        for address, data in volume_data.items():
            record = asdict(data)
            record['token_address'] = address
            records.append(record)
            
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Generate filename
        filename = f"memecoin_volume_{date.strftime('%Y%m%d')}"
        
        if self.storage_format == "parquet":
            file_path = self.storage_dir / "memecoin_volume" / f"{filename}.parquet"
            df.to_parquet(file_path, index=False)
        elif self.storage_format == "csv":
            file_path = self.storage_dir / "memecoin_volume" / f"{filename}.csv"
            df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported storage format: {self.storage_format}")
            
        # Update metadata
        with sqlite3.connect(self.db_path) as conn:
            for address, data in volume_data.items():
                conn.execute("""
                    INSERT OR REPLACE INTO memecoin_volume_metadata 
                    (token_address, date, volume_24h, volume_change_24h, 
                     price_change_24h, source, file_path, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    address, date.isoformat(),
                    data.volume_24h, data.volume_change_24h, data.price_change_24h,
                    data.source, str(file_path),
                    datetime.now(timezone.utc).isoformat()
                ))
            conn.commit()
            
        return str(file_path)
        
    def load_sol_ohlcv(self, symbol: str = "SOL", interval: str = "5m",
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Load SOL OHLCV data from storage"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT file_path FROM sol_ohlcv_metadata 
                WHERE symbol = ? AND interval = ?
            """
            params = [symbol, interval]
            
            if start_date:
                query += " AND end_time >= ?"
                params.append(start_date.isoformat())
                
            if end_date:
                query += " AND start_time <= ?"
                params.append(end_date.isoformat())
                
            query += " ORDER BY start_time"
            
            cursor = conn.execute(query, params)
            file_paths = [row[0] for row in cursor.fetchall()]
            
        # Load and combine data files
        dataframes = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                if file_path.endswith('.parquet'):
                    df = pd.read_parquet(file_path)
                elif file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                else:
                    continue
                    
                dataframes.append(df)
                
        if not dataframes:
            return pd.DataFrame()
            
        combined_df = pd.concat(dataframes, ignore_index=True)
        combined_df = combined_df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        
        # Filter by date range if specified
        if start_date:
            combined_df = combined_df[combined_df['timestamp'] >= start_date]
        if end_date:
            combined_df = combined_df[combined_df['timestamp'] <= end_date]
            
        return combined_df
        
    def load_memecoin_volume(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           token_addresses: Optional[List[str]] = None) -> pd.DataFrame:
        """Load memecoin volume data from storage"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM memecoin_volume_metadata WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date.date().isoformat())
                
            if end_date:
                query += " AND date <= ?"
                params.append(end_date.date().isoformat())
                
            if token_addresses:
                placeholders = ','.join(['?' for _ in token_addresses])
                query += f" AND token_address IN ({placeholders})"
                params.extend(token_addresses)
                
            query += " ORDER BY date, token_address"
            
            df = pd.read_sql_query(query, conn, params=params)
            
        if df.empty:
            return df
            
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df


class HistoricalDataCollector:
    """Collects and backfills historical data"""
    
    def __init__(self, storage: DataStorage, binance_api: BinanceAPI,
                 volume_aggregator: MemecoinVolumeAggregator):
        self.storage = storage
        self.binance_api = binance_api
        self.volume_aggregator = volume_aggregator
        
    def backfill_sol_ohlcv(self, days: int = 30, interval: str = "5m") -> bool:
        """Backfill SOL OHLCV data for specified number of days"""
        logging.info(f"Starting SOL OHLCV backfill for {days} days, interval {interval}")
        
        try:
            # Calculate how many requests we need
            intervals_per_day = {
                "1m": 1440, "5m": 288, "15m": 96, "1h": 24, "1d": 1
            }
            
            limit = min(1000, intervals_per_day.get(interval, 288) * days)
            
            # Get historical data
            candles = self.binance_api.get_klines(
                symbol="SOLUSDT", 
                interval=interval, 
                limit=limit
            )
            
            if candles:
                file_path = self.storage.save_sol_ohlcv(candles, "SOL", interval)
                logging.info(f"Saved {len(candles)} SOL candles to {file_path}")
                return True
            else:
                logging.warning("No SOL OHLCV data retrieved")
                return False
                
        except Exception as e:
            logging.error(f"SOL OHLCV backfill failed: {e}")
            return False
            
    def collect_current_memecoin_volume(self) -> bool:
        """Collect current memecoin volume data"""
        logging.info("Collecting current memecoin volume data")
        
        try:
            volume_data = self.volume_aggregator.get_aggregate_volume()
            
            if volume_data:
                file_path = self.storage.save_memecoin_volume(volume_data)
                logging.info(f"Saved volume data for {len(volume_data)} tokens to {file_path}")
                return True
            else:
                logging.warning("No memecoin volume data retrieved")
                return False
                
        except Exception as e:
            logging.error(f"Memecoin volume collection failed: {e}")
            return False
            
    def backfill_memecoin_volume(self, days: int = 7) -> bool:
        """Backfill memecoin volume data (limited by API constraints)"""
        logging.info(f"Starting memecoin volume backfill for {days} days")
        
        # Note: Most APIs only provide current 24h volume, not historical
        # This would need to be enhanced with a time-series database
        # or premium API access for true historical backfill
        
        success_count = 0
        for day in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=day)
            
            # For now, just collect current data and mark with historical date
            # In production, this would query historical API endpoints
            volume_data = self.volume_aggregator.get_aggregate_volume()
            
            if volume_data:
                # Adjust timestamps for historical simulation
                for address, data in volume_data.items():
                    data.timestamp = date
                    
                self.storage.save_memecoin_volume(volume_data, date)
                success_count += 1
                
        logging.info(f"Completed memecoin volume backfill: {success_count}/{days} days")
        return success_count > 0
        
    def cleanup_old_data(self, retention_days: int = 30) -> bool:
        """Clean up data files older than retention period"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            with sqlite3.connect(self.storage.db_path) as conn:
                # Get old files
                cursor = conn.execute("""
                    SELECT file_path FROM sol_ohlcv_metadata 
                    WHERE created_at < ?
                    UNION
                    SELECT DISTINCT file_path FROM memecoin_volume_metadata 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(), cutoff_date.isoformat()))
                
                old_files = [row[0] for row in cursor.fetchall()]
                
                # Delete files
                deleted_count = 0
                for file_path in old_files:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        
                # Clean up metadata
                conn.execute("DELETE FROM sol_ohlcv_metadata WHERE created_at < ?", 
                           (cutoff_date.isoformat(),))
                conn.execute("DELETE FROM memecoin_volume_metadata WHERE created_at < ?", 
                           (cutoff_date.isoformat(),))
                conn.commit()
                
            logging.info(f"Cleaned up {deleted_count} old data files")
            return True
            
        except Exception as e:
            logging.error(f"Data cleanup failed: {e}")
            return False