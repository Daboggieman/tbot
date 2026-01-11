from .base import BaseCommand

class OrderCommands(BaseCommand):
    def add_arguments(self):
        # Market Order
        market_order_parser = self.parser.add_parser("market-order", help="Place a market order")
        market_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
        market_order_parser.add_argument("order_type", type=str, choices=['buy', 'sell'], help="'buy' or 'sell'")
        market_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
        market_order_parser.add_argument("requested_price", type=float, help="The price the strategy wants")
        market_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
        market_order_parser.add_argument("take_profit", type=float, help="Take profit price")
        market_order_parser.add_argument("slippage", type=int, help="Max slippage in points")

        # Limit Order
        limit_order_parser = self.parser.add_parser("limit-order", help="Place a limit order")
        limit_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
        limit_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
        limit_order_parser.add_argument("price", type=float, help="The limit price")
        limit_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
        limit_order_parser.add_argument("take_profit", type=float, help="Take profit price")

        # Stop Order
        stop_order_parser = self.parser.add_parser("stop-order", help="Place a stop order")
        stop_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
        stop_order_parser.add_argument("volume", type=float, help="e.g., 0.1")
        stop_order_parser.add_argument("price", type=float, help="The stop price")
        stop_order_parser.add_argument("stop_loss", type=float, help="Stop loss price")
        stop_order_parser.add_argument("take_profit", type=float, help="Take profit price")

        # TWAP Order
        twap_order_parser = self.parser.add_parser("twap-order", help="Execute a Time-Weighted Average Price (TWAP) order")
        twap_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
        twap_order_parser.add_argument("total_volume", type=float, help="Total volume to trade")
        twap_order_parser.add_argument("duration_seconds", type=int, help="Duration of the TWAP in seconds")
        twap_order_parser.add_argument("num_chunks", type=int, help="Number of chunks to break the order into")
        twap_order_parser.add_argument("requested_price", type=float, help="The price the strategy wants for each chunk")
        twap_order_parser.add_argument("stop_loss", type=float, help="Stop loss price for each chunk")
        twap_order_parser.add_argument("take_profit", type=float, help="Take profit price for each chunk")
        twap_order_parser.add_argument("slippage", type=int, help="Max slippage in points for each chunk")
        twap_order_parser.add_argument("max_spread", type=int, help="Max spread in points for each chunk")

        # VWAP Order
        vwap_order_parser = self.parser.add_parser("vwap-order", help="Execute a Volume-Weighted Average Price (VWAP) order")
        vwap_order_parser.add_argument("symbol", type=str, help="e.g., EURUSD")
        vwap_order_parser.add_argument("total_volume", type=float, help="Total volume to trade")
        vwap_order_parser.add_argument("duration_seconds", type=int, help="Duration of the VWAP in seconds")
        vwap_order_parser.add_argument("num_chunks", type=int, help="Number of chunks to break the order into")
        vwap_order_parser.add_argument("slippage", type=int, help="Max slippage in points for each chunk")
        vwap_order_parser.add_argument("max_spread", type=int, help="Max spread in points for each chunk")

        # Partial Exit
        partial_exit_parser = self.parser.add_parser("partial-exit", help="Manage partial exit for an open position")
        partial_exit_parser.add_argument("position_id", type=str, help="Identifier for the open position")
        partial_exit_parser.add_argument("percentage_to_close", type=float, help="Percentage of the position volume to close (e.g., 0.25 for 25%)")
        partial_exit_parser.add_argument("current_price", type=float, help="Current market price for the position's symbol")

        # Trailing Stop
        trailing_stop_parser = self.parser.add_parser("trailing-stop", help="Manage a trailing stop-loss for an open position")
        trailing_stop_parser.add_argument("position_id", type=str, help="Identifier for the open position")
        trailing_stop_parser.add_argument("current_price", type=float, help="The current market price")
        trailing_stop_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
        trailing_stop_parser.add_argument("current_stop_loss", type=float, help="The current active stop-loss price")
        trailing_stop_parser.add_argument("trailing_step_points", type=int, help="The number of points the price must move favorably to adjust the stop-loss")

        # Time-based Exit
        time_based_exit_parser = self.parser.add_parser("time-based-exit", help="Manage a time-based exit for an open position")
        time_based_exit_parser.add_argument("position_id", type=str, help="Identifier for the open position")
        time_based_exit_parser.add_argument("reason", type=str, help="Reason for the time-based exit (e.g., 'end_of_day', 'time_limit_reached')")

        # Adjust SL for Volatility
        adjust_sl_volatility_parser = self.parser.add_parser("adjust-sl-volatility", help="Adjust stop-loss based on volatility (e.g., ATR)")
        adjust_sl_volatility_parser.add_argument("position_id", type=str, help="Identifier for the open position")
        adjust_sl_volatility_parser.add_argument("current_price", type=float, help="The current market price")
        adjust_sl_volatility_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
        adjust_sl_volatility_parser.add_argument("current_stop_loss", type=float, help="The current active stop-loss price")
        adjust_sl_volatility_parser.add_argument("atr_value", type=float, help="The Average True Range (ATR) value")
        adjust_sl_volatility_parser.add_argument("atr_multiplier", type=float, default=2.0, help="Multiplier for ATR (default: 2.0)")

        # Manage Profit Targets
        manage_profit_targets_parser = self.parser.add_parser("manage-profit-targets", help="Manage profit targets for an open position")
        manage_profit_targets_parser.add_argument("position_id", type=str, help="Identifier for the open position")
        manage_profit_targets_parser.add_argument("current_price", type=float, help="The current market price")
        manage_profit_targets_parser.add_argument("entry_price", type=float, help="The price at which the position was opened")
        manage_profit_targets_parser.add_argument("profit_target_percent", type=float, help="The profit target as a percentage of the entry price (e.g., 0.02 for 2%)")
        manage_profit_targets_parser.add_argument("trailing_profit_target_percent", type=float, help="The trailing profit target as a percentage (e.g., 0.01 for 1%)")


    def execute(self, args, services):
        order_manager = services.get('order_manager')
        if not order_manager:
            self.logger.error("OrderManager service not available")
            return

        if args.command == "market-order":
            self.logger.info(f"Executing market order command for {args.symbol}")
            order_manager.place_market_order(args.symbol, args.order_type, args.volume, args.requested_price, args.stop_loss, args.take_profit, args.slippage)
        elif args.command == "limit-order":
            self.logger.info(f"Executing limit order command for {args.symbol}")
            order_manager.place_limit_order(args.symbol, args.volume, args.price, args.stop_loss, args.take_profit)
        elif args.command == "stop-order":
            self.logger.info(f"Executing stop order command for {args.symbol}")
            order_manager.place_stop_order(args.symbol, args.volume, args.price, args.stop_loss, args.take_profit)
        elif args.command == "twap-order":
            self.logger.info(f"Executing TWAP order command for {args.symbol}")
            order_manager.place_twap_order(
                symbol=args.symbol,
                total_volume=args.total_volume,
                duration_seconds=args.duration_seconds,
                num_chunks=args.num_chunks,
                requested_price=args.requested_price,
                stop_loss=args.stop_loss,
                take_profit=args.take_profit,
                slippage=args.slippage,
                max_spread=args.max_spread
            )
        elif args.command == "vwap-order":
            self.logger.info(f"Executing VWAP order command for {args.symbol}")
            order_manager.place_vwap_order(
                symbol=args.symbol,
                total_volume=args.total_volume,
                duration_seconds=args.duration_seconds,
                num_chunks=args.num_chunks,
                slippage=args.slippage,
                max_spread=args.max_spread
            )
        elif args.command == "partial-exit":
            self.logger.info(f"Executing partial exit command for position {args.position_id}")
            order_manager.manage_partial_exit(
                position_id=args.position_id,
                percentage_to_close=args.percentage_to_close,
                current_price=args.current_price
            )
        elif args.command == "trailing-stop":
            self.logger.info(f"Executing trailing stop command for position {args.position_id}")
            order_manager.manage_trailing_stop(
                position_id=args.position_id,
                current_price=args.current_price,
                entry_price=args.entry_price,
                current_stop_loss=args.current_stop_loss,
                trailing_step_points=args.trailing_step_points
            )
        elif args.command == "time-based-exit":
            self.logger.info(f"Executing time-based exit command for position {args.position_id}")
            order_manager.manage_time_based_exit(
                position_id=args.position_id,
                reason=args.reason
            )
        elif args.command == "adjust-sl-volatility":
            self.logger.info(f"Executing adjust SL for volatility command for position {args.position_id}")
            order_manager.adjust_sl_for_volatility(
                position_id=args.position_id,
                current_price=args.current_price,
                entry_price=args.entry_price,
                current_stop_loss=args.current_stop_loss,
                atr_value=args.atr_value,
                atr_multiplier=args.atr_multiplier
            )
        elif args.command == "manage-profit-targets":
            self.logger.info(f"Executing manage profit targets command for position {args.position_id}")
            order_manager.manage_profit_targets(
                position_id=args.position_id,
                current_price=args.current_price,
                entry_price=args.entry_price,
                profit_target_percent=args.profit_target_percent,
                trailing_profit_target_percent=args.trailing_profit_target_percent
            )
