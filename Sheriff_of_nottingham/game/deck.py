"""Deck management for Sheriff of Nottingham."""
import random
from typing import List, Optional
from game.cards import Card, CardType, CARD_DATA


class Deck:
    """Manages the draw pile and discard pile."""

    def __init__(self):
        self._draw_pile: List[Card] = []
        self._discard_pile: List[Card] = []
        self._build()
        self.shuffle()

    def _build(self):
        """Build a fresh deck from card data."""
        self._draw_pile.clear()
        for card_type, info in CARD_DATA.items():
            for _ in range(info.count):
                self._draw_pile.append(Card(card_type))

    def shuffle(self):
        """Shuffle the draw pile."""
        random.shuffle(self._draw_pile)

    def draw(self) -> Optional[Card]:
        """Draw one card from the top of the draw pile.
        Reshuffles discard into draw if draw pile is empty."""
        if not self._draw_pile:
            if not self._discard_pile:
                return None
            self._draw_pile = self._discard_pile[:]
            self._discard_pile.clear()
            self.shuffle()
        return self._draw_pile.pop()

    def draw_many(self, count: int) -> List[Card]:
        """Draw multiple cards."""
        return [c for c in (self.draw() for _ in range(count)) if c is not None]

    def discard(self, card: Card):
        """Add a card to the discard pile."""
        self._discard_pile.append(card)

    def discard_many(self, cards: List[Card]):
        """Add multiple cards to the discard pile."""
        self._discard_pile.extend(cards)

    @property
    def market_cards(self) -> List[Card]:
        """View the top 5 cards of the discard as the market."""
        return self._discard_pile[-5:] if len(self._discard_pile) >= 5 else self._discard_pile[:]

    def take_from_market(self, card: Card) -> bool:
        """Remove a specific card from the market (discard pile top)."""
        market = self.market_cards
        if card in market:
            # Find last occurrence in discard pile
            for i in range(len(self._discard_pile) - 1, -1, -1):
                if self._discard_pile[i].card_type == card.card_type:
                    self._discard_pile.pop(i)
                    return True
        return False

    def replenish_market(self, count: int = 5):
        """Ensure the market has at least `count` cards available."""
        needed = count - len(self._discard_pile)
        if needed > 0:
            cards = self.draw_many(needed)
            # Put them face-up into discard (bottom of market stack)
            self._discard_pile = cards + self._discard_pile

    @property
    def draw_pile_size(self) -> int:
        return len(self._draw_pile)

    @property
    def discard_pile_size(self) -> int:
        return len(self._discard_pile)
