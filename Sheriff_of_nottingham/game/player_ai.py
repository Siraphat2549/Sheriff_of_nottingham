"""AI decision-making for Sheriff of Nottingham."""
import random
from typing import List, Tuple, Optional
from collections import Counter
from game.cards import Card, CardType, LEGAL_GOODS, CONTRABAND, LEGAL_GOODS_LIST, CARD_DATA
from game.player import Player


class PlayerAI:
    """Handles all AI decisions for merchant and sheriff roles."""

    def __init__(self, player: Player):
        self.player = player
        self.difficulty = player.ai_difficulty

    # ------------------------------------------------------------------ #
    #  Market Phase                                                        #
    # ------------------------------------------------------------------ #

    def choose_market_action(self, market_cards: List[Card], hand: List[Card]) -> Tuple[str, List[Card]]:
        """Decide what to do in the market phase.
        Returns ('draw', []) to draw 2 from deck,
                ('take_market', [cards]) to take specific market cards.
        """
        # Count contraband in hand
        contraband_count = sum(1 for c in hand if c.is_contraband)

        if self.difficulty == "easy":
            return "draw", []

        # If hand has mostly legal goods, consider taking from market for better contraband
        contraband_in_market = [c for c in market_cards if c.is_contraband]

        if self.difficulty == "hard" and contraband_in_market and contraband_count < 3:
            # Take the most valuable contraband from market
            best = max(contraband_in_market, key=lambda c: c.value)
            return "take_market", [best]

        return "draw", []

    def choose_discards(self, hand: List[Card], max_hand: int = 6) -> List[Card]:
        """Choose which cards to discard to get hand to max_hand size."""
        if len(hand) <= max_hand:
            return []
        excess = len(hand) - max_hand
        # Discard lowest-value legal goods first, keep contraband
        sorted_hand = sorted(hand, key=lambda c: (0 if c.is_contraband else 1, c.value))
        # Actually keep contraband and high-value cards; discard low-value legal
        legal = [c for c in hand if c.is_legal]
        legal_sorted = sorted(legal, key=lambda c: c.value)
        discards = legal_sorted[:excess]
        if len(discards) < excess:
            # Still need to discard more — pick random
            remaining = [c for c in hand if c not in discards]
            discards += random.sample(remaining, excess - len(discards))
        return discards

    # ------------------------------------------------------------------ #
    #  Bag Packing Phase                                                   #
    # ------------------------------------------------------------------ #

    def pack_bag(self, hand: List[Card]) -> Tuple[List[Card], CardType, int]:
        """Decide what to put in the bag and what to declare.
        Returns (bag_cards, declared_type, declared_quantity).
        """
        hand_counts = Counter(c.card_type for c in hand)

        if self.difficulty == "easy":
            return self._pack_honest(hand, hand_counts)

        contraband_cards = [c for c in hand if c.is_contraband]
        legal_cards = [c for c in hand if c.is_legal]

        # Risk assessment based on difficulty and gold
        risk_threshold = {"easy": 0.1, "medium": 0.4, "hard": 0.65}.get(self.difficulty, 0.4)
        if self.player.gold < 15:
            risk_threshold *= 0.7  # Be more conservative when poor

        smuggle = random.random() < risk_threshold and len(contraband_cards) > 0

        if smuggle:
            return self._pack_smuggle(hand, contraband_cards, legal_cards)
        else:
            return self._pack_honest(hand, hand_counts)

    def _pack_honest(self, hand: List[Card], counts: Counter) -> Tuple[List[Card], CardType, int]:
        """Pack bag with all legal goods of the most common type."""
        legal_counts = {ct: cnt for ct, cnt in counts.items() if ct in LEGAL_GOODS and cnt > 0}
        if not legal_counts:
            # No legal goods — pack least-penalising card and bluff it as legal
            if hand:
                card = min(hand, key=lambda c: c.penalty)
                return [card], LEGAL_GOODS_LIST[0], 1
            return [], LEGAL_GOODS_LIST[0], 0

        # Pick legal type with most cards (up to 5)
        best_type = max(legal_counts, key=lambda ct: legal_counts[ct])
        qty = min(legal_counts[best_type], 5)
        cards = [c for c in hand if c.card_type == best_type][:qty]
        return cards, best_type, qty

    def _pack_smuggle(self, hand: List[Card], contraband: List[Card], legal: List[Card]) -> Tuple[List[Card], CardType, int]:
        """Pack bag with contraband, declare as legal goods."""
        # Take up to 3 contraband (more is riskier)
        max_smuggle = {"easy": 1, "medium": 2, "hard": 3}.get(self.difficulty, 2)
        bag_contraband = contraband[:max_smuggle]

        # Fill remaining slots with legal goods for cover (hard AI only)
        bag_legal = []
        if self.difficulty == "hard" and legal:
            fill = min(2, 5 - len(bag_contraband))
            legal_counts = Counter(c.card_type for c in legal)
            best_legal_type = max(legal_counts, key=lambda ct: legal_counts[ct])
            bag_legal = [c for c in legal if c.card_type == best_legal_type][:fill]

        bag = bag_contraband + bag_legal
        if not bag:
            bag = contraband[:1]

        # Declare as the most common legal good type
        declared_type = self._best_legal_to_declare(hand)
        # Declare quantity matching what's in bag (some AIs lie about quantity too)
        declared_qty = len(bag)
        if self.difficulty == "hard" and random.random() < 0.3:
            # Lie about quantity occasionally
            declared_qty = max(1, len(bag) - 1)

        return bag, declared_type, declared_qty

    def _best_legal_to_declare(self, hand: List[Card]) -> CardType:
        """Pick which legal good to declare (most common in hand)."""
        legal_counts = Counter(c.card_type for c in hand if c.is_legal)
        if legal_counts:
            return max(legal_counts, key=legal_counts.get)
        return random.choice(LEGAL_GOODS_LIST)

    # ------------------------------------------------------------------ #
    #  Sheriff Phase                                                       #
    # ------------------------------------------------------------------ #

    def sheriff_decision(self, merchant: Player, round_num: int, total_rounds: int) -> Tuple[str, int]:
        """Decide whether to inspect or let through a merchant's bag.
        Returns ('let_through', 0), ('inspect', 0), or ('accept_bribe', bribe_amount).
        """
        declared_qty = merchant.bag.declared_quantity
        declared_type = merchant.bag.declared_type
        bribe = merchant.bag.bribe_offered

        # Always accept a good bribe
        if bribe > 0:
            bribe_threshold = self._bribe_threshold(declared_qty, round_num, total_rounds)
            if bribe >= bribe_threshold:
                return "accept_bribe", bribe

        suspicion = self._suspicion_score(merchant, round_num, total_rounds)

        if self.difficulty == "easy":
            inspect_prob = 0.2
        elif self.difficulty == "medium":
            inspect_prob = suspicion
        else:
            inspect_prob = min(suspicion * 1.3, 0.9)

        if random.random() < inspect_prob:
            return "inspect", 0
        return "let_through", 0

    def _suspicion_score(self, merchant: Player, round_num: int, total_rounds: int) -> float:
        """Rate 0-1 how suspicious this merchant's declaration is."""
        score = 0.2  # base suspicion
        qty = merchant.bag.declared_quantity

        # More cards = more suspicious
        if qty >= 4:
            score += 0.2
        elif qty >= 3:
            score += 0.1

        # Later in game, be more aggressive
        game_progress = round_num / total_rounds
        score += game_progress * 0.2

        # If merchant has been caught before, less likely to bluff again
        if merchant.times_caught > 0:
            score -= 0.1

        return min(max(score, 0.05), 0.9)

    def _bribe_threshold(self, declared_qty: int, round_num: int, total_rounds: int) -> int:
        """Minimum bribe the AI sheriff will accept."""
        base = declared_qty * 3
        game_progress = round_num / total_rounds
        return int(base * (1 + game_progress))

    def offer_bribe(self, sheriff: Player) -> int:
        """Decide how much gold to offer as bribe to the sheriff."""
        if self.difficulty == "easy":
            return 0
        if self.player.gold < 10:
            return 0
        contraband_in_bag = sum(1 for c in self.player.bag.cards if c.is_contraband)
        if contraband_in_bag == 0:
            return 0
        # Offer proportional to contraband value at risk
        value_at_risk = sum(c.value for c in self.player.bag.cards if c.is_contraband)
        bribe = min(value_at_risk // 2, self.player.gold // 4)
        if self.difficulty == "medium":
            bribe = max(3, bribe)
        return bribe
