import ccxt
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from config import ASSETS, SIGNAL_TYPES, EXPIRY_TIMES, SIGNAL_ACCURACY_THRESHOLD

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': True,  # Use sandbox for testing
            'enableRateLimit': True,
        })
        self.signals_generated = 0
        self.successful_signals = 0
        
    def get_ohlcv_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data from exchange"""
        try:
            # Convert symbol format (e.g., EUR/USD -> EURUSD)
            formatted_symbol = symbol.replace('/', '')
            
            # Get OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"Error getting OHLCV data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        exp1 = df['close'].ewm(span=fast).mean()
        exp2 = df['close'].ewm(span=slow).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    def analyze_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Analyze all technical indicators"""
        if df.empty:
            return {}
        
        # Calculate indicators
        rsi = self.calculate_rsi(df)
        macd, macd_signal, macd_histogram = self.calculate_macd(df)
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df)
        stoch_k, stoch_d = self.calculate_stochastic(df)
        
        # Get latest values
        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_macd = macd.iloc[-1]
        current_macd_signal = macd_signal.iloc[-1]
        current_bb_upper = bb_upper.iloc[-1]
        current_bb_lower = bb_lower.iloc[-1]
        current_stoch_k = stoch_k.iloc[-1]
        current_stoch_d = stoch_d.iloc[-1]
        
        # Analyze signals
        signals = {
            'rsi_signal': None,
            'macd_signal': None,
            'bollinger_signal': None,
            'stochastic_signal': None,
            'overall_signal': None,
            'confidence': 0
        }
        
        # RSI Analysis
        if current_rsi < 30:
            signals['rsi_signal'] = 'BUY'
        elif current_rsi > 70:
            signals['rsi_signal'] = 'SELL'
        
        # MACD Analysis
        if current_macd > current_macd_signal and macd_histogram.iloc[-1] > macd_histogram.iloc[-2]:
            signals['macd_signal'] = 'BUY'
        elif current_macd < current_macd_signal and macd_histogram.iloc[-1] < macd_histogram.iloc[-2]:
            signals['macd_signal'] = 'SELL'
        
        # Bollinger Bands Analysis
        if current_price <= current_bb_lower:
            signals['bollinger_signal'] = 'BUY'
        elif current_price >= current_bb_upper:
            signals['bollinger_signal'] = 'SELL'
        
        # Stochastic Analysis
        if current_stoch_k < 20 and current_stoch_d < 20:
            signals['stochastic_signal'] = 'BUY'
        elif current_stoch_k > 80 and current_stoch_d > 80:
            signals['stochastic_signal'] = 'SELL'
        
        # Overall signal calculation
        buy_signals = sum(1 for signal in signals.values() if signal == 'BUY')
        sell_signals = sum(1 for signal in signals.values() if signal == 'SELL')
        
        if buy_signals > sell_signals and buy_signals >= 2:
            signals['overall_signal'] = 'BUY'
            signals['confidence'] = min(buy_signals / 4 * 100, 95)
        elif sell_signals > buy_signals and sell_signals >= 2:
            signals['overall_signal'] = 'SELL'
            signals['confidence'] = min(sell_signals / 4 * 100, 95)
        
        return signals
    
    def generate_signal(self, asset: str) -> Optional[Dict]:
        """Generate trading signal for given asset"""
        try:
            # Get market data
            df = self.get_ohlcv_data(asset)
            if df.empty:
                return None
            
            # Analyze technical indicators
            analysis = self.analyze_technical_indicators(df)
            
            if not analysis or analysis['overall_signal'] is None:
                return None
            
            # Check confidence threshold
            if analysis['confidence'] < SIGNAL_ACCURACY_THRESHOLD * 100:
                return None
            
            # Determine signal type
            signal_type = 'CALL' if analysis['overall_signal'] == 'BUY' else 'PUT'
            
            # Select expiry time based on volatility
            current_price = df['close'].iloc[-1]
            price_change = abs((current_price - df['close'].iloc[-2]) / df['close'].iloc[-2])
            
            if price_change > 0.002:  # High volatility
                expiry_time = '1m'
            elif price_change > 0.001:  # Medium volatility
                expiry_time = '5m'
            else:  # Low volatility
                expiry_time = '15m'
            
            # Calculate entry price and targets
            entry_price = current_price
            if signal_type == 'CALL':
                target_price = entry_price * 1.001  # 0.1% profit target
                stop_loss = entry_price * 0.999  # 0.1% stop loss
            else:
                target_price = entry_price * 0.999  # 0.1% profit target
                stop_loss = entry_price * 1.001  # 0.1% stop loss
            
            signal = {
                'asset': asset,
                'signal_type': signal_type,
                'expiry_time': expiry_time,
                'entry_price': round(entry_price, 5),
                'target_price': round(target_price, 5),
                'stop_loss': round(stop_loss, 5),
                'accuracy': round(analysis['confidence'], 2),
                'analysis': analysis,
                'timestamp': datetime.now()
            }
            
            self.signals_generated += 1
            logger.info(f"Generated signal: {signal}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {asset}: {e}")
            return None
    
    def generate_signals_for_all_assets(self) -> List[Dict]:
        """Generate signals for all configured assets"""
        signals = []
        
        for asset in ASSETS:
            try:
                signal = self.generate_signal(asset)
                if signal:
                    signals.append(signal)
                
                # Add delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error generating signal for {asset}: {e}")
                continue
        
        return signals
    
    def update_signal_result(self, signal_id: int, result: str):
        """Update signal result and statistics"""
        if result == 'WIN':
            self.successful_signals += 1
        
        logger.info(f"Signal {signal_id} result: {result}")
    
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if self.signals_generated == 0:
            return 0.0
        return (self.successful_signals / self.signals_generated) * 100
    
    def get_statistics(self) -> Dict:
        """Get signal generation statistics"""
        return {
            'total_signals': self.signals_generated,
            'successful_signals': self.successful_signals,
            'success_rate': self.get_success_rate(),
            'last_generated': datetime.now()
        } 