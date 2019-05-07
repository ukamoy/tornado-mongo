from .client import Client
from .consts import *


class FutureAPI(Client):

    def __init__(self, api_key, api_seceret_key, passphrase, use_server_time=False):
        Client.__init__(self, api_key, api_seceret_key, passphrase, use_server_time)

    # query position
    """{'result': True, 'margin_mode': 'crossed', 'holding': [
        {'instrument_id': 'EOS-USD-181026', 'long_settlement_price': '5.433', 'short_qty': '0', 'liquidation_price': '2.404', 
        'long_avg_cost': '5.433', 'long_qty': '1', 'short_settlement_price': '0', 'long_avail_qty': '1', 'realised_pnl': '-0.00055218', 
        'created_at': '2018-10-22T06:52:26.0Z', 'updated_at': '2018-10-22T07:52:20.0Z', 'short_avg_cost': '0', 'leverage': '10', 
        'short_avail_qty': '0'}]}
    """
    def get_position(self):
        return self._request_without_params(GET, FUTURE_POSITION)

    # query specific position
    """{'margin_mode': 'cross', 'holding': [
        {'short_qty': '0', 'short_settlement_price': '0', 'updated_at': '2018-10-22T07:40:58.0Z', 'long_qty': '0', 'long_avail_qty': '0', 
        'long_avg_cost': '0', 'short_avail_qty': '0', 'leverage': '10', 'long_settlement_price': '0', 'instrument_id': 'EOS-USD-181026', 
        'short_avg_cost': '0', 'created_at': '2018-10-22T06:52:26.0Z', 'realised_pnl': '0', 'liquidation_price': '0.0'}], 'result': True}
    """
    def get_specific_position(self, instrument_id):
        return self._request_without_params(GET, FUTURE_SPECIFIC_POSITION + str(instrument_id) + '/position')

    # query accounts info
    """
    {'result': True, 'info': {
    'etc': {'margin_mode': 'crossed', 'total_avail_balance': '0', 'realized_pnl': '0', 'equity': '0', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'bch': {'margin_mode': 'crossed', 'total_avail_balance': '0', 'realized_pnl': '0', 'equity': '0', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'xrp': {'margin_mode': 'crossed', 'total_avail_balance': '0', 'realized_pnl': '0', 'equity': '0', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'btc': {'margin_mode': 'crossed', 'total_avail_balance': '0', 'realized_pnl': '0', 'equity': '0', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'eos': {'margin_mode': 'crossed', 'total_avail_balance': '2.361', 'realized_pnl': '0', 'equity': '2.361', 'margin_ratio': '12.329', 'margin': '0.191', 'unrealized_pnl': '0'}, 
    'btg': {'margin_mode': 'crossed', 'total_avail_balance': '0', 'realized_pnl': '0', 'equity': '0', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'ltc': {'margin_mode': 'crossed', 'total_avail_balance': '0.0000005', 'realized_pnl': '0', 'equity': '0.0000005', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}, 
    'eth': {'margin_mode': 'crossed', 'total_avail_balance': '0.039', 'realized_pnl': '0', 'equity': '0.039', 'margin_ratio': '10000', 'margin': '0', 'unrealized_pnl': '0'}}}
    """
    def get_accounts(self):

        return self._request_without_params(GET, FUTURE_ACCOUNTS)

    # query coin account info
    """
    {'realized_pnl': '0', 'unrealized_pnl': '0', 'equity': '0', 'total_avail_balance': '0', 'margin': '0', 
    'margin_mode': 'crossed', 'margin_ratio': '10000'}
    """
    def get_coin_account(self, symbol):
        return self._request_without_params(GET, FUTURE_COIN_ACCOUNT + str(symbol))

    # query leverage
    """
    {'data': {'leverage': 10, 'margin_mode': 'cross_margin', 'currency': 'BTC'}, 'code': 0, 'msg': 'success', 'detailMsg': ''}
    """
    def get_leverage(self, symbol):
        return self._request_without_params(GET, FUTURE_GET_LEVERAGE + str(symbol) + '/leverage')

    # set leverage
    """ 
    new leverage {'radio': 20, 'currency': 'EOS', 'margin_mode': 'cross_margin', 'result': 'true'}
    already in use  {'msg': 'success', 'data': '', 'detailMsg': '', 'code': 0}
    """
    def set_leverage(self, symbol, instrument_id='', direction='', leverage=10):
        #params = {'margin_mode': margin_mode, 'instrument_id': instrument_id, 'direction': direction, 'ratio': ratio}
        params = {'instrument_id': instrument_id, 'direction': direction, 'leverage': leverage}
        if symbol:
            return self._request_with_params(POST, FUTURE_SET_LEVERAGE + str(symbol) + '/leverage', params)
        else:
            return self._request_with_params(POST, FUTURE_SET_LEVERAGE + 'leverage', params)

    # query ledger
    """{'amount': '-0.00051617', 'ledger_id': '1599916812304385', 'type': 'fee', 'currency': 'EOS', 
    'timestamp': '2018-10-10T05:19:53.0Z', 'balance': '0', 
    'details': {'order_id': 1599916807492608, 'instrument_id': 'EOS-USD-181228', 'type': 'match'}}"""
    def get_ledger(self, symbol):
        return self._request_without_params(GET, FUTURE_LEDGER + str(symbol) + '/ledger')

    # delete position
    """骗人的，取消了"""
    # def revoke_position(self, position_data):
    #     params = {'position_data': position_data}
    #     return self._request_with_params(DELETE, FUTURE_DELETE_POSITION, params)
    def revoke_position(self, position_data):
        params = {'position_data': position_data}
        return self._request_with_params(POST, FUTURE_DELETE_POSITION, params)

    # take order
    """{'error_message': '', 'order_id': '1668343327628288', 'result': True, 'error_code': 0}"""
    def take_order(self, instrument_id, otype, price, size, margin_mode, match_price, client_oid):
        # params = {'instrument_id': instrument_id, 'otype': otype, 'price': price, 'order': order_Qty, 'match_price': match_price, 'client_id': client_id}
        params = {'instrument_id': instrument_id, 'type': otype, 'price': price, 'size':size, 'margin_mode':margin_mode, 'match_price':match_price, 'client_oid':client_oid}
        return self._request_with_params(POST, FUTURE_ORDER, params)

    #take orders
    """待测试"""
    def take_orders(self, instrument_id, order_data, leverage):
        params = {'instrument_id': instrument_id, 'order_data': order_data, 'leverage': leverage}
        return self._request_with_params(POST, FUTURE_ORDERS, params)

    # revoke order
    """{'order_id': '1668343327628288', 'result': True}"""
    def revoke_order(self, instrument_id, order_id):
        return self._request_without_params(POST, FUTURE_REVOKE_ORDER + str(instrument_id) + '/' + str(order_id))

    # revoke orders
    """待测试"""
    def revoke_orders(self, instrument_id):
        return self._request_without_params(POST, FUTURE_REVOKE_ORDERS+str(instrument_id))

    # query order list
    #def get_order_list(self, state, before, after, limit, instrument_id=''):
    #   params = {'state': state, 'before': before, 'after': after, 'limit': limit, 'instrument_id': instrument_id}
    #    return self._request_with_params(GET, FUTURE_ORDERS_LIST, params)

    # query order list
    """https://www.okex.com/api/futures/v3/orders/EOS-USD-181026?instrument_id=EOS-USD-181026&state=0
    {'result': True, 'order_info': [
    {'instrument_id': 'EOS-USD-181026', 'fee': '0', 'type': '1', 'price': '5.222', 'filled_qty': '0', 
    'contract_val': '10', 'size': '1', 'state': '0', 'price_avg': '0', 
    'create_date': '2018-10-23T03:50:08.0Z', 'leverage': '10', 'order_id': '1673173977765888'}, 
    {'instrument_id': 'EOS-USD-181026', 'fee': '0', 'type': '1', 'price': '5.111', 'filled_qty': '0', 
    'contract_val': '10', 'size': '1', 'state': '0', 'price_avg': '0', 
    'create_date': '2018-10-23T03:50:15.0Z', 'leverage': '10', 'order_id': '1673174406897664'}]}"""
    def get_order_list(self, state, froms=0, to=0, limit=0, instrument_id=''):
        params = {'state': state}
        if froms:
            params['from'] = froms
        if to:
            params['to'] = to
        if limit:
            params['limit'] = limit
        if instrument_id:
            params['instrument_id'] = instrument_id
        return self._request_with_params(GET, FUTURE_ORDERS_LIST + '/' + str(instrument_id) , params)

    # query order info
    """{'instrument_id': 'EOS-USD-181026', 'fee': '0', 'order_id': '1668419337141248', 'contract_val': '10', 
    'create_date': '2018-10-22T07:40:58.0Z', 'price': '5.223', 'size': '1', 'filled_qty': '0', 'state': '0', 
    'type': '1', 'price_avg': '0', 'leverage': '10'}"""
    def get_order_info(self, order_id, instrument_id):
        return self._request_without_params(GET, FUTURE_ORDER_INFO + str(instrument_id) + '/' + str(order_id))

    # query fills
    #def get_fills(self, order_id, instrument_id, before, after, limit):
    #    params = {'order_id': order_id, 'before': before, 'after': after, 'limit': limit, 'instrument_id': instrument_id}
    #    return self._request_with_params(GET, FUTURE_FILLS, params)

    # query fills
    """
    [{'order_qty': '1', 'instrument_id': 'EOS-USD-181026', 'created_at': '2018-10-22T07:51:44.0Z', 'trade_id': '1668461671383051', 
    'order_id': '1668461669555202', 'price': '5.433', 'fee': '-0.00055218', 'exec_type': 'T'}]"""

    def get_fills(self, order_id, instrument_id, froms, to, limit):
        params = {'order_id': order_id, 'from': froms, 'to': to, 'limit': limit, 'instrument_id': instrument_id}
        return self._request_with_params(GET, FUTURE_FILLS, params)

    # get products info
    """{
        'contract_val': '100',
        'trade_increment': '1',
        'underlying_index': 'BTC',
        'instrument_id': 'BTC-USD-181026',
        'delivery': '2018-10-26',
        'quote_currency': 'USD',
        'tick_size': '0.01',
        'listing': '2018-10-12'
    },
    {
        'contract_val': '100',
        'trade_increment': '1',
        'underlying_index': 'BTC',
        'instrument_id': 'BTC-USD-181102',
        'delivery': '2018-11-02',
        'quote_currency': 'USD',
        'tick_size': '0.01',
        'listing': '2018-10-19'
    },
    {
        'contract_val': '100',
        'trade_increment': '1',
        'underlying_index': 'BTC',
        'instrument_id': 'BTC-USD-181228',
        'delivery': '2018-12-28',
        'quote_currency': 'USD',
        'tick_size': '0.01',
        'listing': '2018-09-14'
    },"""
    def get_products(self):
        return self._request_without_params(GET, FUTURE_PRODUCTS_INFO)

    # get depth
    """
    {'bids': [[6434.3, 40, 0, 1], [6434.28, 174, 0, 1], [6433.98, 17, 0, 1], [6433.97, 12, 0, 1], [6433.24, 1, 0, 1]], 
    'asks': [[6434.31, 38, 0, 1], [6435.22, 20, 0, 2], [6435.88, 60, 0, 2], [6436.11, 40, 0, 2], [6436.22, 20, 0, 2]], 
    'timestamp': '2018-10-22T03:38:28.358Z'}"""
    def get_depth(self, instrument_id, size):
        params = {'size': size}
        return self._request_with_params(GET, FUTURE_DEPTH + str(instrument_id) + '/book', params)

    # get ticker  (see below)
    def get_ticker(self):
        return self._request_without_params(GET, FUTURE_TICKER)

    # get specific ticker
    """{
  'volume_24h': '796052',
  'last': '6436.25',
  'timestamp': '2018-10-22T04:09:23.040Z',
  'low_24h': '6408.32',
  'best_bid': '6436.82',
  'instrument_id': 'BTC-USD-181026',
  'best_ask': '6437.19',
  'high_24h': '6473.16'}
    """
    def get_specific_ticker(self, instrument_id):
        return self._request_without_params(GET, FUTURE_SPECIFIC_TICKER + str(instrument_id) + '/ticker')

    # query trades
    # def get_trades(self, instrument_id, before, after, limit):
    #    params = {'before': before, 'after': after, 'limit': limit}
    #    return self._request_with_params(GET, FUTURE_TRADES + str(instrument_id) + '/trades', params, cursor=True)

    # query trades v3
    """{'trade_id': '1667597275332626', 'side': 'sell', 'qty': '100', 'timestamp': '2018-10-22T04:11:55.70Z', 'price': '6437.42'}"""
    def get_trades(self, instrument_id, froms, to, limit):
        params = {'from': froms, 'to': to, 'limit': limit}
        return self._request_with_params(GET, FUTURE_TRADES + str(instrument_id) + '/trades', params, cursor=True)

    # query k-line
    """[ time, open, high, low, close, volume, volume_to_currency ]
    [1540177200000,6430.84,6437.87,6430.84,6436.92,19852,308.52759178679975]"""
    def get_kline(self, instrument_id, granularity, start='', end=''):
        params = {'granularity': granularity, 'start': start, 'end': end}
        return self._request_with_params(GET, FUTURE_KLINE + str(instrument_id) + '/candles', params)

    # query index
    """ {'timestamp': '2018-10-22T03:53:10.635Z', 'instrument_id': 'EOS-USD-181026', 'index': '5.39'}"""
    def get_index(self, instrument_id):
        return self._request_without_params(GET, FUTURE_INDEX + str(instrument_id) + '/index')

    # query rate
    """{'rate': '6.913', 'instrument_id': 'USD_CNY'}"""
    def get_rate(self):
        return self._request_without_params(GET, FUTURE_RATE)

    # query estimate price
    """{'timestamp': '2018-10-22T03:56:10.970Z', 'instrument_id': 'BTC-USD-181026', 'settlement_price': '0'}"""
    def get_estimated_price(self, instrument_id):
        return self._request_without_params(GET, FUTURE_ESTIMAT_PRICE + str(instrument_id) + '/estimated_price')

    # query the total platform of the platform
    """{'amount': '732790', 'instrument_id': 'BTC-USD-181026', 'timestamp': '2018-10-22T03:56:37.447Z'}"""
    def get_holds(self, instrument_id):
        return self._request_without_params(GET, FUTURE_HOLDS + str(instrument_id) + '/open_interest')

    # query limit price
    """{'timestamp': '2018-10-22T03:57:05.199Z', 'highest': '6630.89', 'instrument_id': 'BTC-USD-181026', 'lowest': '6244'}"""
    def get_limit(self, instrument_id):
        return self._request_without_params(GET, FUTURE_LIMIT + str(instrument_id) + '/price_limit')

    # query liquidation
    def get_liquidation(self, instrument_id):
        return self._request_without_params(GET, FUTURE_LIQUIDATION + str(instrument_id) + '/liquidation')

    # query mark price
    """{'instrument_id': 'BTC-USD-181026', 'mark_price': 6436.03, 'timestamp': '2018-10-22T03:57:43.872Z'}"""
    def get_mark_price(self, instrument_id):
        return self._request_without_params(GET, FUTURE_MARK + str(instrument_id) + '/mark_price')
    
    # get_currencies
    """[{"min_size": "0.00000001", "name": "BTC", "id": "0"}, 
    {"min_size": "0.00000001", "name": "LTC", "id": "1"}, 
    {"min_size": "0.00000001", "name": "ETH", "id": "2"}, 
    {"min_size": "0.00000001", "name": "ETC", "id": "4"}, 
    {"min_size": "0.00000001", "name": "BCH", "id": "5"}, 
    {"min_size": "0.00000001", "name": "XRP", "id": "15"}, 
    {"min_size": "0.00000001", "name": "EOS", "id": "20"}, 
    {"min_size": "0.00000001", "name": "BTG", "id": "10"}]"""
    def get_currencies(self):
        return self._request_without_params(GET, CURRENCY_LIST)