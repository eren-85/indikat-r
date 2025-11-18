"""
Pattern Lifecycle Management System

Manages pattern states (pending, active, completed) and tracks TP/Stop hits
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class PatternState(Enum):
    """Pattern lifecycle states"""
    PENDING = "pending"      # Pattern identified but not yet confirmed
    ACTIVE = "active"        # Pattern confirmed and position active
    TP_HIT = "tp_hit"       # Take profit reached
    STOP_HIT = "stop_hit"   # Stop loss hit
    EXPIRED = "expired"     # Pattern expired without TP/Stop


@dataclass
class PatternSignal:
    """Universal pattern signal structure"""
    pattern_type: str       # "H&S", "Gartley", "Bull Flag", etc.
    pattern_id: str         # Unique identifier
    side: str              # "long" or "short"

    # Entry details
    entry_time: pd.Timestamp
    entry_price: float
    entry_index: int

    # Risk management
    stop_price: float
    tp1_price: float
    tp2_price: Optional[float] = None

    # Pattern specific data
    pattern_data: dict = None

    # Lifecycle
    state: PatternState = PatternState.ACTIVE
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # Performance
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    r_multiple: Optional[float] = None

    # Timeframe limits
    max_bars: Optional[int] = None
    bars_active: int = 0


class PatternManager:
    """
    Manages all patterns and their lifecycle

    Tracks:
    - Pattern entry/exit
    - TP/Stop monitoring
    - Pattern expiration
    - Statistics
    """

    def __init__(self, ohlc: pd.DataFrame):
        """
        Initialize pattern manager

        Parameters:
        -----------
        ohlc : pd.DataFrame
            OHLC data with datetime index
        """
        self.ohlc = ohlc
        self.index = ohlc.index
        self.high = ohlc['high'].to_numpy()
        self.low = ohlc['low'].to_numpy()
        self.close = ohlc['close'].to_numpy()

        self.patterns: List[PatternSignal] = []
        self.active_patterns: List[PatternSignal] = []
        self.completed_patterns: List[PatternSignal] = []

        self._next_id = 0

    def add_pattern(
        self,
        pattern_type: str,
        side: str,
        entry_index: int,
        entry_price: float,
        stop_price: float,
        tp1_price: float,
        tp2_price: Optional[float] = None,
        max_bars: Optional[int] = None,
        pattern_data: dict = None
    ) -> PatternSignal:
        """
        Add a new pattern

        Parameters:
        -----------
        pattern_type : str
            Pattern name
        side : str
            "long" or "short"
        entry_index : int
            Index in OHLC data
        entry_price : float
            Entry price
        stop_price : float
            Stop loss price
        tp1_price : float
            First take profit
        tp2_price : float, optional
            Second take profit
        max_bars : int, optional
            Maximum bars before expiration
        pattern_data : dict, optional
            Additional pattern-specific data

        Returns:
        --------
        PatternSignal
            Created pattern signal
        """

        pattern_id = f"{pattern_type}_{self._next_id}"
        self._next_id += 1

        pattern = PatternSignal(
            pattern_type=pattern_type,
            pattern_id=pattern_id,
            side=side,
            entry_time=self.index[entry_index],
            entry_price=entry_price,
            entry_index=entry_index,
            stop_price=stop_price,
            tp1_price=tp1_price,
            tp2_price=tp2_price,
            max_bars=max_bars,
            pattern_data=pattern_data or {}
        )

        self.patterns.append(pattern)
        self.active_patterns.append(pattern)

        return pattern

    def update_patterns(self, current_index: int):
        """
        Update all active patterns based on current price

        Parameters:
        -----------
        current_index : int
            Current candle index
        """

        if current_index >= len(self.high):
            return

        current_high = self.high[current_index]
        current_low = self.low[current_index]
        current_close = self.close[current_index]
        current_time = self.index[current_index]

        patterns_to_remove = []

        for pattern in self.active_patterns:
            # Skip if pattern is in the future
            if pattern.entry_index > current_index:
                continue

            # Update bars active
            pattern.bars_active = current_index - pattern.entry_index

            # Check expiration
            if pattern.max_bars and pattern.bars_active >= pattern.max_bars:
                self._close_pattern(
                    pattern,
                    current_time,
                    current_close,
                    "expired"
                )
                patterns_to_remove.append(pattern)
                continue

            # Check TP/Stop hits
            if pattern.side == "long":
                # Long position checks
                if current_low <= pattern.stop_price:
                    # Stop hit
                    self._close_pattern(
                        pattern,
                        current_time,
                        pattern.stop_price,
                        "stop_hit"
                    )
                    patterns_to_remove.append(pattern)
                elif current_high >= pattern.tp1_price:
                    # TP1 hit
                    self._close_pattern(
                        pattern,
                        current_time,
                        pattern.tp1_price,
                        "tp_hit"
                    )
                    patterns_to_remove.append(pattern)

            else:  # short
                # Short position checks
                if current_high >= pattern.stop_price:
                    # Stop hit
                    self._close_pattern(
                        pattern,
                        current_time,
                        pattern.stop_price,
                        "stop_hit"
                    )
                    patterns_to_remove.append(pattern)
                elif current_low <= pattern.tp1_price:
                    # TP1 hit
                    self._close_pattern(
                        pattern,
                        current_time,
                        pattern.tp1_price,
                        "tp_hit"
                    )
                    patterns_to_remove.append(pattern)

        # Remove completed patterns from active list
        for pattern in patterns_to_remove:
            self.active_patterns.remove(pattern)
            self.completed_patterns.append(pattern)

    def _close_pattern(
        self,
        pattern: PatternSignal,
        exit_time: pd.Timestamp,
        exit_price: float,
        reason: str
    ):
        """Close a pattern and calculate performance"""

        pattern.exit_time = exit_time
        pattern.exit_price = exit_price
        pattern.exit_reason = reason

        # Update state
        if reason == "stop_hit":
            pattern.state = PatternState.STOP_HIT
        elif reason == "tp_hit":
            pattern.state = PatternState.TP_HIT
        else:
            pattern.state = PatternState.EXPIRED

        # Calculate PnL
        if pattern.side == "long":
            pattern.pnl = exit_price - pattern.entry_price
            pattern.pnl_percent = (pattern.pnl / pattern.entry_price) * 100
        else:
            pattern.pnl = pattern.entry_price - exit_price
            pattern.pnl_percent = (pattern.pnl / pattern.entry_price) * 100

        # Calculate R-multiple
        risk = abs(pattern.entry_price - pattern.stop_price)
        if risk > 0:
            pattern.r_multiple = pattern.pnl / risk
        else:
            pattern.r_multiple = 0.0

    def get_active_patterns(
        self,
        current_index: int,
        pattern_types: Optional[List[str]] = None,
        sides: Optional[List[str]] = None
    ) -> List[PatternSignal]:
        """
        Get currently active patterns

        Parameters:
        -----------
        current_index : int
            Current candle index
        pattern_types : list, optional
            Filter by pattern types
        sides : list, optional
            Filter by side ("long", "short")

        Returns:
        --------
        list of PatternSignal
            Active patterns matching filters
        """

        # Update patterns first
        self.update_patterns(current_index)

        result = self.active_patterns.copy()

        # Apply filters
        if pattern_types:
            result = [p for p in result if p.pattern_type in pattern_types]

        if sides:
            result = [p for p in result if p.side in sides]

        return result

    def get_statistics(self) -> dict:
        """Get pattern performance statistics"""

        if not self.completed_patterns:
            return {
                "total": 0,
                "win_rate": 0,
                "avg_r": 0,
                "profit_factor": 0
            }

        wins = [p for p in self.completed_patterns if p.state == PatternState.TP_HIT]
        losses = [p for p in self.completed_patterns if p.state == PatternState.STOP_HIT]

        total = len(self.completed_patterns)
        win_rate = len(wins) / total * 100 if total > 0 else 0

        avg_r = np.mean([p.r_multiple for p in self.completed_patterns])

        gross_profit = sum([p.pnl for p in wins]) if wins else 0
        gross_loss = abs(sum([p.pnl for p in losses])) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            "total": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "avg_r": avg_r,
            "profit_factor": profit_factor,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss
        }

    def to_dataframe(self, active_only: bool = False) -> pd.DataFrame:
        """
        Convert patterns to DataFrame

        Parameters:
        -----------
        active_only : bool
            If True, only return active patterns

        Returns:
        --------
        pd.DataFrame
            Pattern data
        """

        patterns = self.active_patterns if active_only else self.patterns

        if not patterns:
            return pd.DataFrame()

        data = []
        for p in patterns:
            data.append({
                'pattern_id': p.pattern_id,
                'pattern_type': p.pattern_type,
                'side': p.side,
                'state': p.state.value,
                'entry_time': p.entry_time,
                'entry_price': p.entry_price,
                'stop_price': p.stop_price,
                'tp1_price': p.tp1_price,
                'exit_time': p.exit_time,
                'exit_price': p.exit_price,
                'exit_reason': p.exit_reason,
                'pnl': p.pnl,
                'pnl_percent': p.pnl_percent,
                'r_multiple': p.r_multiple,
                'bars_active': p.bars_active
            })

        return pd.DataFrame(data)


def calculate_pattern_max_bars(pattern_type: str, pole_width: int = None) -> int:
    """
    Calculate max bars for pattern based on type

    Per YouTube transcripts:
    - H&S: Use head width as time limit
    - Flags: Use flag width or pole width
    - Harmonics: Use XA to D distance

    Parameters:
    -----------
    pattern_type : str
        Pattern type
    pole_width : int, optional
        Width of pattern (pattern-specific)

    Returns:
    --------
    int
        Maximum bars before expiration
    """

    if pole_width:
        return pole_width

    # Default timeouts by pattern type
    defaults = {
        "H&S": 50,
        "Inverse H&S": 50,
        "Bull Flag": 30,
        "Bear Flag": 30,
        "Bull Pennant": 30,
        "Bear Pennant": 30,
        "Gartley": 40,
        "Bat": 40,
        "Butterfly": 40,
        "Crab": 40,
        "Deep Crab": 40,
        "Cypher": 40,
        "Shark": 40
    }

    return defaults.get(pattern_type, 50)
