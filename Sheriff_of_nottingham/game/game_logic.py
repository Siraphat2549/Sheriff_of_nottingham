"""Core game engine for Sheriff of Nottingham."""
from typing import List, Dict, Optional, Tuple
from collections import Counter
from enum import Enum, auto
from game.cards import Card, CardType, LEGAL_GOODS, LEGAL_GOODS_LIST, CARD_DATA
from game.deck import Deck
from game.player import Player
from game.player_ai import PlayerAI


class GamePhase(Enum):
    SETUP = auto()
    MARKET = auto()
    PACK_BAG = auto()
    INSPECTION = auto()
    ROUND_END = auto()
    GAME_END = auto()


class InspectionResult(Enum):
    LET_THROUGH = "let_through"
    CAUGHT = "caught"
    HONEST = "honest"
    BRIBE_ACCEPTED = "bribe_accepted"


class RoundEvent:
    """Records what happened during inspection of one merchant."""

    def __init__(self, merchant_name: str, declared_type: CardType,
                 declared_qty: int, actual_cards: List[Card],
                 result: InspectionResult, gold_change_merchant: int,
                 gold_change_sheriff: int, bribe: int = 0):
        self.merchant_name = merchant_name
        self.declared_type = declared_type
        self.declared_qty = declared_qty
        self.actual_cards = actual_cards
        self.result = result
        self.gold_change_merchant = gold_change_merchant
        self.gold_change_sheriff = gold_change_sheriff
        self.bribe = bribe


class GameEngine:
    """Manages all game state and rules."""

    HAND_SIZE = 6
    MARKET_SIZE = 5
    MAX_BAG_CARDS = 5
    MIN_BAG_CARDS = 1

    def __init__(self):
        self.players: List[Player] = []
        self.deck: Optional[Deck] = None
        self.phase: GamePhase = GamePhase.SETUP
        self.current_round: int = 0
        self.total_rounds: int = 0
        self.sheriff_index: int = 0
        self.current_merchant_index: int = 0  # index in merchant_order
        self.merchant_order: List[int] = []   # player indices for this round
        self.round_events: List[RoundEvent] = []
        self.all_round_events: List[List[RoundEvent]] = []
        self.market_cards: List[Card] = []    # 5 face-up market cards
        self._ai_controllers: Dict[str, PlayerAI] = {}

    # ------------------------------------------------------------------ #
    #  Game Setup                                                          #
    # ------------------------------------------------------------------ #

    def setup_game(self, player_configs: List[Dict]) -> None:
        """
        player_configs: list of dicts with keys 'name', 'is_ai', 'ai_difficulty'
        First entry is always the human player.
        """
        if not (2 <= len(player_configs) <= 5):
            raise ValueError("Sheriff of Nottingham requires 2-5 players.")

        self.players = []
        for cfg in player_configs:
            p = Player(cfg["name"], cfg.get("is_ai", False), cfg.get("ai_difficulty", "medium"))
            self.players.append(p)

        # AI controllers
        self._ai_controllers = {}
        for p in self.players:
            if p.is_ai:
                self._ai_controllers[p.name] = PlayerAI(p)

        n = len(self.players)
        self.total_rounds = n * (2 if n <= 4 else 1)
        self.current_round = 0
        self.sheriff_index = 0

        self.deck = Deck()
        self._deal_initial_hands()
        self._setup_market()
        self.phase = GamePhase.MARKET
        self._start_new_round()

    def _deal_initial_hands(self):
        """Deal 6 cards to each player."""
        for player in self.players:
            player.hand = self.deck.draw_many(self.HAND_SIZE)

    def _setup_market(self):
        """Initialise market with 5 face-up cards."""
        self.market_cards = self.deck.draw_many(self.MARKET_SIZE)

    def _start_new_round(self):
        """Advance to the next round."""
        self.current_round += 1
        self.round_events = []
        # Build merchant order (everyone except the sheriff)
        self.merchant_order = [i for i in range(len(self.players)) if i != self.sheriff_index]
        self.current_merchant_index = 0
        self.phase = GamePhase.MARKET

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    @property
    def sheriff(self) -> Player:
        return self.players[self.sheriff_index]

    @property
    def human_player(self) -> Player:
        return self.players[0]

    @property
    def current_merchant(self) -> Optional[Player]:
        if self.current_merchant_index < len(self.merchant_order):
            return self.players[self.merchant_order[self.current_merchant_index]]
        return None

    def is_human_sheriff(self) -> bool:
        return not self.sheriff.is_ai

    def is_human_merchant_turn(self) -> bool:
        m = self.current_merchant
        return m is not None and not m.is_ai

    # ------------------------------------------------------------------ #
    #  Market Phase                                                        #
    # ------------------------------------------------------------------ #

    def market_draw_from_deck(self, player: Player) -> List[Card]:
        """Player draws 2 cards from the deck."""
        cards = self.deck.draw_many(2)
        player.add_to_hand(cards)
        return cards

    def market_take_from_market(self, player: Player, card: Card) -> bool:
        """Player takes one card from the market; returns True if successful."""
        if card in self.market_cards:
            self.market_cards.remove(card)
            player.add_to_hand([card])
            # Replenish market
            new_card = self.deck.draw()
            if new_card:
                self.market_cards.append(new_card)
            return True
        return False

    def market_discard(self, player: Player, cards: List[Card]):
        """Player discards cards from hand to the market/discard pile."""
        for card in cards:
            if player.remove_from_hand(card):
                self.deck.discard(card)
                # Optionally add to market if space
                if len(self.market_cards) < self.MARKET_SIZE:
                    self.market_cards.append(card)

    def ai_do_market_phase(self, player: Player):
        """Auto-run the market phase for an AI player."""
        ai = self._ai_controllers[player.name]
        action, chosen_cards = ai.choose_market_action(self.market_cards, player.hand)
        if action == "take_market" and chosen_cards:
            for card in chosen_cards:
                self.market_take_from_market(player, card)
        else:
            self.market_draw_from_deck(player)

        # Discard if over hand limit
        if player.hand_size > self.HAND_SIZE:
            discards = ai.choose_discards(player.hand, self.HAND_SIZE)
            self.market_discard(player, discards)

    def advance_market_phase(self):
        """Move to the next merchant in market phase, or transition to pack-bag."""
        self.current_merchant_index += 1
        if self.current_merchant_index >= len(self.merchant_order):
            self.current_merchant_index = 0
            self.phase = GamePhase.PACK_BAG

    def run_all_ai_market(self):
        """Run market phase for all AI merchants sequentially, skipping human."""
        for idx in self.merchant_order:
            p = self.players[idx]
            if p.is_ai:
                self.ai_do_market_phase(p)

    # ------------------------------------------------------------------ #
    #  Pack Bag Phase                                                      #
    # ------------------------------------------------------------------ #

    def pack_player_bag(self, player: Player, cards: List[Card],
                        declared_type: CardType, declared_qty: int) -> bool:
        """Pack the player's bag. Returns True if valid."""
        if not (self.MIN_BAG_CARDS <= len(cards) <= self.MAX_BAG_CARDS):
            return False
        if declared_type not in LEGAL_GOODS:
            return False
        if not (1 <= declared_qty <= self.MAX_BAG_CARDS):
            return False
        # Remove cards from hand
        removed = player.remove_many_from_hand(cards)
        if len(removed) != len(cards):
            # Put removed back and fail
            player.add_to_hand(removed)
            return False
        player.pack_bag(removed, declared_type, declared_qty)
        return True

    def ai_pack_bag(self, player: Player):
        """Auto-pack bag for an AI player."""
        ai = self._ai_controllers[player.name]
        cards, declared_type, declared_qty = ai.pack_bag(player.hand)
        if cards:
            # Remove cards from hand
            removed = player.remove_many_from_hand(cards)
            player.pack_bag(removed, declared_type, declared_qty)
        else:
            # Fallback: pack 1 legal card honestly if available, else pack any card
            legal = [c for c in player.hand if c.is_legal]
            if legal:
                card = legal[0]
                player.remove_from_hand(card)
                player.pack_bag([card], card.card_type, 1)
            elif player.hand:
                card = player.hand[0]
                player.remove_from_hand(card)
                player.pack_bag([card], LEGAL_GOODS_LIST[0], 1)

    def advance_pack_bag_phase(self):
        """Move to the next merchant in pack-bag phase, or transition to inspection."""
        self.current_merchant_index += 1
        if self.current_merchant_index >= len(self.merchant_order):
            self.current_merchant_index = 0
            self.phase = GamePhase.INSPECTION

    def run_all_ai_pack_bag(self):
        """Pack bags for all AI merchants."""
        for idx in self.merchant_order:
            p = self.players[idx]
            if p.is_ai:
                self.ai_pack_bag(p)

    # ------------------------------------------------------------------ #
    #  Inspection Phase                                                    #
    # ------------------------------------------------------------------ #

    def sheriff_inspect(self, merchant: Player) -> RoundEvent:
        """Sheriff opens the merchant's bag. Resolve penalties/compensation."""
        is_honest = merchant.bag.is_honest()
        actual_cards = merchant.bag.cards[:]
        declared_type = merchant.bag.declared_type
        declared_qty = merchant.bag.declared_quantity
        sheriff = self.sheriff

        if is_honest:
            # Sheriff pays 2 gold per card in bag as compensation
            compensation = len(actual_cards) * 2
            paid = sheriff.pay_gold(compensation)
            merchant.earn_gold(paid)
            merchant.accept_bag_into_stall()
            merchant.times_inspected += 1
            result = InspectionResult.HONEST
            event = RoundEvent(merchant.name, declared_type, declared_qty, actual_cards,
                               result, paid, -paid)
        else:
            # Merchant pays penalty for each illegal card
            penalty = 0
            illegal_cards = []
            for card in actual_cards:
                if card.card_type != declared_type:
                    penalty += card.penalty
                    illegal_cards.append(card)

            paid = merchant.pay_gold(penalty)
            sheriff.earn_gold(paid)
            merchant.times_caught += 1
            merchant.times_inspected += 1

            # Legal cards still go to stall; contraband is confiscated
            legal_stall = [c for c in actual_cards if c.card_type == declared_type]
            confiscated = [c for c in actual_cards if c.card_type != declared_type]
            merchant.stall.extend(legal_stall)
            self.deck.discard_many(confiscated)
            merchant.bag.clear()

            result = InspectionResult.CAUGHT
            event = RoundEvent(merchant.name, declared_type, declared_qty, actual_cards,
                               result, -paid, paid)

        self.round_events.append(event)
        return event

    def sheriff_let_through(self, merchant: Player) -> RoundEvent:
        """Sheriff lets the merchant through without inspection."""
        actual_cards = merchant.bag.cards[:]
        declared_type = merchant.bag.declared_type
        declared_qty = merchant.bag.declared_quantity

        if merchant.bag.bribe_offered > 0:
            # Sheriff accepted a bribe
            bribe = merchant.bag.bribe_offered
            merchant.pay_gold(bribe)
            self.sheriff.earn_gold(bribe)
            result = InspectionResult.BRIBE_ACCEPTED
        else:
            result = InspectionResult.LET_THROUGH

        if merchant.bag.is_honest():
            for c in actual_cards:
                if c.is_contraband:
                    merchant.successful_smuggles += 1
                    break

        merchant.accept_bag_into_stall()
        event = RoundEvent(merchant.name, declared_type, declared_qty, actual_cards,
                           result, 0, 0, merchant.bag.bribe_offered)
        self.round_events.append(event)
        return event

    def ai_sheriff_decide(self, merchant: Player) -> Tuple[str, RoundEvent]:
        """AI sheriff decides what to do with a merchant. Returns (action, event)."""
        ai = self._ai_controllers[self.sheriff.name]
        decision, _ = ai.sheriff_decision(merchant, self.current_round, self.total_rounds)
        if decision == "inspect":
            event = self.sheriff_inspect(merchant)
            return "inspect", event
        elif decision == "accept_bribe":
            event = self.sheriff_let_through(merchant)
            return "accept_bribe", event
        else:
            event = self.sheriff_let_through(merchant)
            return "let_through", event

    def run_all_ai_inspections(self) -> List[RoundEvent]:
        """Run inspection for all AI merchants when human is sheriff."""
        # This shouldn't be called normally; human sheriff acts manually
        events = []
        for idx in self.merchant_order:
            p = self.players[idx]
            if p.is_ai:
                _, event = self.ai_sheriff_decide(p)
                events.append(event)
        return events

    def advance_inspection_phase(self) -> bool:
        """Move to next merchant in inspection. Returns True if round is over."""
        self.current_merchant_index += 1
        if self.current_merchant_index >= len(self.merchant_order):
            self.phase = GamePhase.ROUND_END
            self.all_round_events.append(self.round_events[:])
            return True
        return False

    # ------------------------------------------------------------------ #
    #  Round End / Game End                                               #
    # ------------------------------------------------------------------ #

    def end_round(self):
        """Transition from round end to next round or game end."""
        if self.current_round >= self.total_rounds:
            self.phase = GamePhase.GAME_END
        else:
            self.sheriff_index = (self.sheriff_index + 1) % len(self.players)
            self._start_new_round()

    def calculate_final_scores(self) -> List[Dict]:
        """Compute final scores for all players including bonuses."""
        counts_per_player: Dict[str, Counter] = {p.name: p.stall_counts for p in self.players}

        king_of: Dict[CardType, Optional[str]] = {}
        queen_of: Dict[CardType, Optional[str]] = {}

        for card_type in LEGAL_GOODS:
            amounts = [(p.name, counts_per_player[p.name].get(card_type, 0)) for p in self.players]
            amounts.sort(key=lambda x: -x[1])
            king_of[card_type] = amounts[0][0] if amounts[0][1] > 0 else None
            if len(amounts) > 1 and amounts[1][1] > 0 and amounts[1][0] != amounts[0][0]:
                queen_of[card_type] = amounts[1][0]
            else:
                queen_of[card_type] = None

        scores = []
        for player in self.players:
            stall_value = player.stall_value
            bonus_total = 0
            bonuses = []
            for card_type in LEGAL_GOODS:
                info = CARD_DATA[card_type]
                if king_of[card_type] == player.name:
                    bonus_total += info.king_bonus
                    bonuses.append(f"King of {card_type.value} +{info.king_bonus}")
                elif queen_of[card_type] == player.name:
                    bonus_total += info.queen_bonus
                    bonuses.append(f"Queen of {card_type.value} +{info.queen_bonus}")

            total = player.gold + stall_value + bonus_total
            scores.append({
                "name": player.name,
                "gold": player.gold,
                "stall_value": stall_value,
                "bonus": bonus_total,
                "bonus_details": bonuses,
                "total": total,
                "stall_counts": dict(counts_per_player[player.name]),
                "is_ai": player.is_ai,
            })

        scores.sort(key=lambda s: -s["total"])
        return scores
