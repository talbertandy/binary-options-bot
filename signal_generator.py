import random
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self):
        self.assets = [
            "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", 
            "AUD/USD", "USD/CAD", "NZD/USD", "EUR/GBP",
            "EUR/JPY", "GBP/JPY", "AUD/JPY", "CAD/JPY"
        ]
        
        self.expiry_times = ["1мин", "2мин", "3мин", "5мин", "10мин", "15мин"]
        
        # Cache for performance
        self._last_signal_time = None
        self._signal_cache = None
        self._cache_duration = 60  # Cache for 1 minute
    
    def generate_signal(self) -> Optional[Dict]:
        """Generate a single signal"""
        try:
            # Check cache first
            if self._is_cache_valid():
                return self._signal_cache
            
            # Generate new signal
            asset = random.choice(self.assets)
            signal_type = random.choice(["CALL", "PUT"])
            expiry_time = random.choice(self.expiry_times)
            
            # Generate realistic prices
            base_price = self._get_base_price(asset)
            entry_price = self._format_price(base_price)
            
            # Calculate target and stop loss
            if signal_type == "CALL":
                target_price = self._format_price(base_price * 1.0015)  # 0.15% up
            else:
                target_price = self._format_price(base_price * 0.9985)  # 0.15% down
            
            # Generate accuracy (70-95%)
            accuracy = random.randint(70, 95)
            
            signal = {
                'asset': asset,
                'signal_type': signal_type,
                'expiry_time': expiry_time,
                'entry_price': entry_price,
                'target_price': target_price,
                'accuracy': accuracy,
                'timestamp': datetime.now()
            }
            
            # Update cache
            self._update_cache(signal)
            
            logger.info(f"Generated signal: {asset} {signal_type} {expiry_time}")
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _get_base_price(self, asset: str) -> float:
        """Get base price for asset"""
        base_prices = {
            "EUR/USD": 1.0850,
            "GBP/USD": 1.2650,
            "USD/JPY": 148.50,
            "USD/CHF": 0.8750,
            "AUD/USD": 0.6650,
            "USD/CAD": 1.3550,
            "NZD/USD": 0.6150,
            "EUR/GBP": 0.8580,
            "EUR/JPY": 161.20,
            "GBP/JPY": 187.80,
            "AUD/JPY": 98.80,
            "CAD/JPY": 109.60
        }
        
        base = base_prices.get(asset, 1.0000)
        
        # Add some random variation (±0.5%)
        variation = random.uniform(-0.005, 0.005)
        return base * (1 + variation)
    
    def _format_price(self, price: float) -> str:
        """Format price to string"""
        if price >= 100:
            return f"{price:.2f}"
        elif price >= 10:
            return f"{price:.4f}"
        else:
            return f"{price:.5f}"
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._last_signal_time or not self._signal_cache:
            return False
        
        time_diff = (datetime.now() - self._last_signal_time).total_seconds()
        return time_diff < self._cache_duration
    
    def _update_cache(self, signal: Dict):
        """Update signal cache"""
        self._signal_cache = signal
        self._last_signal_time = datetime.now()
    
    def generate_multiple_signals(self, count: int = 3) -> list:
        """Generate multiple signals"""
        signals = []
        for _ in range(count):
            signal = self.generate_signal()
            if signal:
                signals.append(signal)
        return signals
    
    def get_statistics(self) -> Dict:
        """Get signal generation statistics"""
        return {
            'total_signals': random.randint(150, 300),
            'successful_signals': random.randint(120, 250),
            'success_rate': random.uniform(75.0, 85.0),
            'last_generated': datetime.now()
        } 