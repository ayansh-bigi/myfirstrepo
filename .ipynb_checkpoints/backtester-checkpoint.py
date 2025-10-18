import pandas as pd
import matplotlib.pyplot as plt
import panel as pn
import panel as pn
import plotly.graph_objects as go
pn.extension('plotly', 'tabulator')


class BackTester:
    def __init__(self, data, slippage=10, cooling_period=1, marker_offset=100):
        self.data = data.copy()
        self.slippage = slippage  # fixed slippage in points
        self.cooling_period = cooling_period
        self.marker_offset = marker_offset
        self.data['Position'] = 0
        self.trades = pd.DataFrame(columns=[
            'TradeID', 'Side', 'EntryIndex', 'ExitIndex', 'EntryPrice', 'ExitPrice', 
            'TradeReturnPct', 'UnderlyingChange', 'PnL', 'CumulativePnL', 
            'CashInjection', 'CumulativeCashRequired', 'Duration'
        ])

    # run_backtest and performance_summary are expected to be defined elsewhere in the module        

    def run_backtest(self, entry_cond_long, exit_cond_long, entry_cond_short=None, exit_cond_short=None):
        in_trade = False
        trade_side = None
        entry_price = None
        entry_index = None
        trade_id = 0
        bars_since_exit = 999  # large so it allows entry at start

        cumulative_pnl = 1.0
        cumulative_cash = 1.0

        equity_history = []
        cash_history = []

        for i in range(1, len(self.data)-1):
            prev = self.data.iloc[i-1]
            curr = self.data.iloc[i]
            next_bar = self.data.iloc[i+1]

            # Entry check (only if not in trade and cooling period passed)
            if not in_trade and bars_since_exit >= self.cooling_period:
                if entry_cond_long(prev, curr):
                    in_trade = True
                    trade_side = 'long'
                    entry_price = next_bar['Open'] + self.slippage/2
                    entry_index = i+1
                    trade_id += 1
                    bars_since_exit = 0
                elif entry_cond_short and entry_cond_short(prev, curr):
                    in_trade = True
                    trade_side = 'short'
                    entry_price = next_bar['Open'] - self.slippage/2
                    entry_index = i+1
                    trade_id += 1
                    bars_since_exit = 0

            # Exit check
            if in_trade:
                exit_cond_met = False
                if trade_side == 'long' and exit_cond_long(prev, curr):
                    exit_cond_met = True
                    exit_price = next_bar['Open'] - self.slippage/2
                elif trade_side == 'short' and exit_cond_short and exit_cond_short(prev, curr):
                    exit_cond_met = True
                    exit_price = next_bar['Open'] + self.slippage/2

                if exit_cond_met:
                    exit_index = i+1
                    duration = exit_index - entry_index + 1

                    if trade_side == 'long':
                        trade_return_pct = (exit_price - entry_price)/entry_price * 100
                        underlying_change = exit_price - entry_price
                    else:
                        trade_return_pct = (entry_price - exit_price)/entry_price * 100
                        underlying_change = entry_price - exit_price

                    pnl = trade_return_pct / 100
                    cumulative_pnl += pnl
                    cash_injection = max(0, 1 - cumulative_pnl)
                    cumulative_pnl += cash_injection
                    cumulative_cash += cash_injection

                    self.trades = pd.concat([self.trades, pd.DataFrame([{
                        'TradeID': trade_id,
                        'Side': trade_side,
                        'EntryIndex': entry_index,
                        'ExitIndex': exit_index,
                        'EntryPrice': entry_price,
                        'ExitPrice': exit_price,
                        'TradeReturnPct': trade_return_pct,
                        'UnderlyingChange': underlying_change,
                        'PnL': pnl,
                        'CumulativePnL': cumulative_pnl,
                        'CashInjection': cash_injection,
                        'CumulativeCashRequired': cumulative_cash,
                        'Duration': duration
                    }])], ignore_index=True)

                    # Reset trade
                    in_trade = False
                    trade_side = None
                    entry_price = None
                    bars_since_exit = 0  # reset after exit

            if not in_trade:
                bars_since_exit += 1

            equity_history.append(cumulative_pnl)
            cash_history.append(cumulative_cash)

        # Align to data index
        pnl_series = pd.Series(index=self.trades['ExitIndex'], data=self.trades['CumulativePnL'])
        cash_series = pd.Series(index=self.trades['ExitIndex'], data=self.trades['CumulativeCashRequired'])
        
        self.data['CumulativePnL'] = pnl_series.reindex(self.data.index).ffill().fillna(1)
        self.data['CumulativeCashRequired'] = cash_series.reindex(self.data.index).ffill().fillna(1)
        self.data['EquityValue'] = equity_history + [cumulative_pnl]*(len(self.data) - len(equity_history))
        self.data['CashDeployed'] = cash_history + [cumulative_cash]*(len(self.data) - len(cash_history))
        return self.trades


    def plot_results(self):
        fig, axs = plt.subplots(3, 2, figsize=(16, 12))

        # Equity Value
        axs[0,0].plot(self.data.index, self.data['EquityValue'], label='Equity Value')
        axs[0,0].set_title('Equity Value Over Time')
        axs[0,0].legend()

        # Cash Deployed
        axs[0,1].plot(self.data.index, self.data['CashDeployed'], label='Cash Deployed', color='orange')
        axs[0,1].set_title('Cash Deployed Over Time')
        axs[0,1].legend()

        # Long Trade Returns Histogram
        long_returns = self.trades[self.trades['Side']=='long']['TradeReturnPct']
        axs[1,0].hist(long_returns, bins=20, alpha=0.7, color='green')
        axs[1,0].set_title('Long Trade Returns (%)')

        # Short Trade Returns Histogram
        short_returns = self.trades[self.trades['Side']=='short']['TradeReturnPct']
        axs[1,1].hist(short_returns, bins=20, alpha=0.7, color='red')
        axs[1,1].set_title('Short Trade Returns (%)')

        # Long Underlying Change Histogram
        long_underlying = self.trades[self.trades['Side']=='long']['UnderlyingPctChange']
        axs[2,0].hist(long_underlying, bins=20, alpha=0.7, color='green')
        axs[2,0].set_title('Long Underlying Change (%)')

        # Short Underlying Change Histogram
        short_underlying = self.trades[self.trades['Side']=='short']['UnderlyingPctChange']
        axs[2,1].hist(short_underlying, bins=20, alpha=0.7, color='red')
        axs[2,1].set_title('Short Underlying Change (%)')

        plt.tight_layout()
        plt.show()


   
        
    def performance_summary(self):
        df = self.trades.copy()
        if df.empty:
            return pd.DataFrame()

        summary = {}
        for side in ['long','short']:
            side_df = df[df['Side']==side]
            summary[f'HitRatio_{side}'] = round((side_df['PnL']>0).mean()*100,2) if not side_df.empty else 0
            summary[f'AvgReturn_{side}'] = round(side_df['TradeReturnPct'].mean(),2) if not side_df.empty else 0
            summary[f'StdReturn_{side}'] = round(side_df['TradeReturnPct'].std(),2) if not side_df.empty else 0
            summary[f'AvgUnderlyingMove_{side}'] = round(side_df['UnderlyingChange'].abs().mean(),2) if not side_df.empty else 0
            summary[f'AvgSlippage_{side}'] = round((side_df['UnderlyingChange'].abs() - side_df['TradeReturnPct']/100*side_df['EntryPrice']).mean(),2) if not side_df.empty else 0
            summary[f'AvgDurationProfitable_{side}'] = round(side_df[side_df['PnL']>0]['Duration'].mean(),2) if not side_df.empty else 0
            summary[f'AvgDurationLoss_{side}'] = round(side_df[side_df['PnL']<=0]['Duration'].mean(),2) if not side_df.empty else 0

        summary['HitRatio_Total'] = round((df['PnL']>0).mean()*100,2)
        summary['MaxDrawdown'] = round((df['CumulativePnL'].cummax() - df['CumulativePnL']).max(),2)
        summary['TotalCashDeployed'] = round(df['CumulativeCashRequired'].iloc[-1],2) if not df.empty else 1
        summary['CumulativePnL_End'] = round(df['CumulativePnL'].iloc[-1],2) if not df.empty else 1

        # Convert to two-column DataFrame
        summary_df = pd.DataFrame({'Attribute':list(summary.keys()), 'Value':list(summary.values())})
        return summary_df

    
    import panel as pn
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    
    
#     def panel_dashboard(self):
#         # === Performance summary ===
#         summary_data = pd.DataFrame({
#             "Parameter": ["Total Trades", "Win Rate", "Avg PnL", "Total PnL"],
#             "Value": [
#                 len(self.trades),
#                 f"{(self.trades['PnL'] > 0).mean() * 100:.1f}%",
#                 f"{self.trades['PnL'].mean() * 100:.2f}%",
#                 f"{self.trades['PnL'].sum() * 100:.2f}%"
#             ]
#         })

#         perf_table = pn.pane.DataFrame(summary_data, width=400, height=150, index=False)


#         # === Equity Curve ===
#         fig_eq, ax_eq = plt.subplots(figsize=(5,3))
#         cum_pnl = self.trades['PnL'].cumsum()
#         ax_eq.plot(cum_pnl, label='Cumulative PnL')
#         ax_eq.legend()
#         ax_eq.set_title('Equity Curve')
#         equity_panel = pn.pane.Matplotlib(fig_eq, tight=True, sizing_mode='stretch_both')


#         # === OHLC chart with trade markers ===
#         fig = go.Figure(data=[go.Candlestick(
#         x=self.data.index.astype(str),
#         open=self.data['Open'],
#         high=self.data['High'],
#         low=self.data['Low'],
#         close=self.data['Close'],
#         name="OHLC",
#         showlegend=False
#         )])


#         # Add trade markers with offsets
#         for _, trade in self.trades.iterrows():
#             entry_idx = trade['EntryIndex']
#             exit_idx = trade['ExitIndex']
#             entry_date = str(self.data.index[entry_idx])
#             exit_date = str(self.data.index[exit_idx])


#         if trade["Side"] == "long":
#             y_entry = self.data.loc[self.data.index[entry_idx], "Low"] - 100
#             y_exit = self.data.loc[self.data.index[exit_idx], "Low"] - 100
#             fig.add_annotation(x=entry_date, y=y_entry, text="LO", showarrow=False, font=dict(color="green", size=12))
#             fig.add_annotation(x=exit_date, y=y_exit, text="LS", showarrow=False, font=dict(color="green", size=12))
#         else:
#             y_entry = self.data.loc[self.data.index[entry_idx], "High"] + 100
#             y_exit = self.data.loc[self.data.index[exit_idx], "High"] + 100
#             fig.add_annotation(x=entry_date, y=y_entry, text="SO", showarrow=False, font=dict(color="red", size=12))
#             fig.add_annotation(x=exit_date, y=y_exit, text="SE", showarrow=False, font=dict(color="red", size=12))


#         fig.update_layout(
#         xaxis_title=None,
#         yaxis_title="Price",
#         xaxis=dict(showticklabels=True, tickangle=0, tickfont=dict(size=9)),
#         showlegend=False,
#         margin=dict(l=0, r=0, t=20, b=0),
#         height=700
#         )


#         ohlc_panel = pn.pane.Plotly(fig, sizing_mode='stretch_both')


#         # === Tabs ===
#         dashboard = pn.Tabs(
#         ("Summary", pn.Column(perf_table, equity_panel, sizing_mode='stretch_both')),
#         ("OHLC Trades", ohlc_panel)
#         )


#         return dashboard



    def performance_summary(self):
        df = self.trades.copy()
        if df.empty:
            return pd.DataFrame({'Attribute':[], 'Value':[]})

        summary = {}
        summary['TotalTrades'] = len(df)
        summary['WinRate_Total'] = round((df['PnL'] > 0).mean() * 100, 2)
        summary['AvgPnLPct'] = round(df['TradeReturnPct'].mean(), 2)
        summary['TotalPnL%'] = round(df['TradeReturnPct'].sum(), 2)

        # Durations by side and profit/loss
        for side in ['long', 'short']:
            side_df = df[df['Side'] == side]
            summary[f'AvgDurationProfitable_{side}'] = round(side_df[side_df['PnL']>0]['Duration'].mean(), 2) if not side_df.empty else 0.0
            summary[f'AvgDurationLoss_{side}'] = round(side_df[side_df['PnL']<=0]['Duration'].mean(), 2) if not side_df.empty else 0.0

        # Other stats
        for side in ['long', 'short']:
            side_df = df[df['Side'] == side]
            summary[f'HitRatio_{side}'] = round((side_df['PnL']>0).mean()*100, 2) if not side_df.empty else 0.0
            summary[f'AvgReturn_{side}_pct'] = round(side_df['TradeReturnPct'].mean(), 2) if not side_df.empty else 0.0
            summary[f'StdReturn_{side}_pct'] = round(side_df['TradeReturnPct'].std(), 2) if not side_df.empty else 0.0
            summary[f'AvgUnderlyingMove_{side}_pts'] = round(side_df['UnderlyingChange'].abs().mean(), 2) if not side_df.empty else 0.0
            # slippage measured as difference between underlying move and realized pnl in pts
            if not side_df.empty:
                slippage_pts = (side_df['UnderlyingChange'].abs() - (side_df['TradeReturnPct']/100.0 * side_df['EntryPrice']).abs()).mean()
                summary[f'AvgSlippagePts_{side}'] = round(slippage_pts, 2)
            else:
                summary[f'AvgSlippagePts_{side}'] = 0.0

        # Max drawdown based on cumulative pnl
        if not df.empty:
            cum = pd.Series(df['CumulativePnL'].values)
            roll_max = cum.cummax()
            max_dd = ((roll_max - cum) / roll_max).max()
            summary['MaxDrawdown'] = round(max_dd, 4)
        else:
            summary['MaxDrawdown'] = 0.0

        summary['TotalCashDeployed'] = round(df['CumulativeCashRequired'].iloc[-1], 4) if not df.empty else 1.0
        summary['CumulativePnL_End'] = round(df['CumulativePnL'].iloc[-1], 4) if not df.empty else 1.0

        # Convert to two-column dataframe
        summary_df = pd.DataFrame({'Attribute': list(summary.keys()), 'Value': list(summary.values())})
        return summary_df

    def panel_dashboard(self):
        # --- Tab 1: Analytics (2x2 charts and summary table in right column spanning rows) ---
        # Chart A: Equity Value
        fig_eq, ax_eq = plt.subplots(figsize=(6,3))
        ax_eq.plot(self.data.index, self.data['EquityValue'])
        ax_eq.set_xticklabels(self.data.index.strftime("%d-%b-%y")[::max(1, len(self.data)//10)],rotation=90)
        ax_eq.set_title('Equity Value')
        ax_eq.grid(True)
        chart_eq = pn.pane.Matplotlib(fig_eq, tight=True, sizing_mode='stretch_both')

        # Chart B: Cumulative Cash Required
        fig_cash, ax_cash = plt.subplots(figsize=(6,3))
        ax_cash.plot(self.data.index, self.data['CumulativeCashRequired'])
        ax_cash.set_title('Cumulative Cash Required')
        ax_cash.grid(True)
        chart_cash = pn.pane.Matplotlib(fig_cash, tight=True, sizing_mode='stretch_both')

        # Chart C: Distribution - Long returns
        fig_long, ax_long = plt.subplots(figsize=(6,3))
        long_returns = self.trades[self.trades['Side']=='long']['TradeReturnPct']
        if not long_returns.empty:
            ax_long.hist(long_returns, bins=20, alpha=0.8)
        ax_long.set_title('Distribution of Long Returns (%)')
        chart_long = pn.pane.Matplotlib(fig_long, tight=True, sizing_mode='stretch_both')

        # Chart D: Distribution - Short returns
        fig_short, ax_short = plt.subplots(figsize=(6,3))
        short_returns = self.trades[self.trades['Side']=='short']['TradeReturnPct']
        if not short_returns.empty:
            ax_short.hist(short_returns, bins=20, alpha=0.8, color='red')
        ax_short.set_title('Distribution of Short Returns (%)')
        chart_short = pn.pane.Matplotlib(fig_short, tight=True, sizing_mode='stretch_both')

        # Summary table (right column spanning two rows)
        summary_df = self.performance_summary()
        summary_panel = pn.pane.DataFrame(summary_df, sizing_mode='stretch_both', width=360)

        grid = pn.GridSpec(sizing_mode='stretch_both', max_height=900)
        grid[0,0] = chart_eq
        grid[0,1] = chart_cash
        grid[1,0] = chart_long
        grid[1,1] = chart_short
        grid[0:2,2] = summary_panel  # merged column for table
        grid[2,0:2] = self.trades

        analytics_tab = pn.Column(grid, sizing_mode='stretch_both')

        # --- Tab 2: OHLC Candles full screen with markers ---
        fig = go.Figure()
        # Candles with string x-axis for equal spacing
        fig.add_trace(go.Candlestick(
            x=[str(x) for x in self.data.index],
            open=self.data['Open'],
            high=self.data['High'],
            low=self.data['Low'],
            close=self.data['Close'],
            name='OHLC',
            showlegend=False,
            increasing_line_color='green',   # color for up candles
            decreasing_line_color='red',     # color for down candles
            increasing_fillcolor='green',    # optional: fill for up candles
            decreasing_fillcolor='red'       # optional: fill for down candles
        ))

        # Add entry/exit markers using markers + text as required
        for _, trade in self.trades.iterrows():
            try:
                entry_idx = int(trade['EntryIndex'])
                exit_idx = int(trade['ExitIndex'])
            except Exception:
                continue

            entry_x = str(self.data.index[entry_idx])
            exit_x = str(self.data.index[exit_idx])

            if trade['Side'] == 'long':
                # LO/LS 100 points below Low
                y_entry = self.data.iloc[entry_idx]['Low'] - self.marker_offset
                y_exit = self.data.iloc[exit_idx]['Low'] - self.marker_offset
                fig.add_trace(go.Scatter(x=[entry_x], y=[y_entry], mode='text', text=['LO'], textfont=dict(color='green', size=12), showlegend=False))
                fig.add_trace(go.Scatter(x=[exit_x], y=[y_exit], mode='text', text=['LE'], textfont=dict(color='green', size=12), showlegend=False))
            else:
                # SO/SE 100 points above High
                y_entry = self.data.iloc[entry_idx]['High'] + self.marker_offset
                y_exit = self.data.iloc[exit_idx]['High'] + self.marker_offset
                fig.add_trace(go.Scatter(x=[entry_x], y=[y_entry], mode='text', text=['SO'], textfont=dict(color='red', size=12), showlegend=False))
                fig.add_trace(go.Scatter(x=[exit_x], y=[y_exit], mode='text', text=['SE'], textfont=dict(color='red', size=12), showlegend=False))

        #fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_white', height=800, showlegend=False, margin=dict(l=20, r=20, t=30, b=30))
        
        fig.update_layout(
                            xaxis=dict(
                                title="Time",
                                type="category",          # <--- this removes time-based spacing
                                tickmode="array",
                                tickvals=self.data.index[::max(1, len(self.data)//10)],
                                ticktext=[t.strftime("%b %d") for t in self.data.index[::max(1, len(self.data)//10)]],
                            ),
                            yaxis_title="Price",
                            height=600,
                            showlegend=False,
                            margin=dict(l=40, r=20, t=30, b=40)
                        )
        
        
        ohlc_panel = pn.pane.Plotly(fig, sizing_mode='stretch_both')

        tabs = pn.Tabs(('Analytics', analytics_tab), ('OHLC Trades', ohlc_panel))
        return tabs
