import random
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self):
        self.signals_generated = 0
        self.successful_signals = 0
        self.assets = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'EUR/GBP', 'USD/CHF', 'AUD/USD']
        self.signal_types = ['CALL', 'PUT']
        self.expiry_times = ['1m', '2m', '5m', '15m']
        
    def generate_signal(self, asset: str = None) -> Optional[Dict]:
        """Generate trading signal for given asset"""
        try:
            # Use provided asset or random one
            if not asset:
                asset = random.choice(self.assets)
            
            # Generate random but realistic signal
            signal_type = random.choice(self.signal_types)
            expiry_time = random.choice(self.expiry_times)
            
            # Generate realistic prices (simplified)
            base_price = random.uniform(1.0500, 1.3500) if 'USD' in asset else random.uniform(100.0, 150.0)
            
            # Calculate entry and target prices
            if signal_type == 'CALL':
                entry_price = base_price
                target_price = entry_price * 1.0015  # 0.15% profit
                stop_loss = entry_price * 0.9985    # 0.15% loss
            else:  # PUT
                entry_price = base_price
                target_price = entry_price * 0.9985  # 0.15% profit
                stop_loss = entry_price * 1.0015    # 0.15% loss
            
            # Generate realistic accuracy (70-95%)
            accuracy = random.uniform(70, 95)
            
            signal = {
                'asset': asset,
                'signal_type': signal_type,
                'expiry_time': expiry_time,
                'entry_price': round(entry_price, 5),
                'target_price': round(target_price, 5),
                'stop_loss': round(stop_loss, 5),
                'accuracy': round(accuracy, 2),
                'timestamp': datetime.now()
            }
            
            self.signals_generated += 1
            logger.info(f"Generated signal: {signal}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def generate_signals_for_all_assets(self) -> List[Dict]:
        """Generate signals for all assets"""
        signals = []
        for asset in self.assets:
            signal = self.generate_signal(asset)
            if signal:
                signals.append(signal)
        return signals
    
    def update_signal_result(self, signal_id: int, result: str):
        """Update signal result (simplified)"""
        if result == 'win':
            self.successful_signals += 1
        logger.info(f"Signal {signal_id} result: {result}")
    
    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.signals_generated == 0:
            return 0.0
        return (self.successful_signals / self.signals_generated) * 100
    
    def get_statistics(self) -> Dict:
        """Get signal statistics"""
        return {
            'total_signals': self.signals_generated,
            'successful_signals': self.successful_signals,
            'success_rate': self.get_success_rate(),
            'last_generated': datetime.now()
        } 