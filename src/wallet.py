import os
import orjson
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class AgentWallet:
    def __init__(self):
        self.file_path = "./data/wallet.json"
        MANTA_RPC_URL = Web3.HTTPProvider(os.getenv("MANTA_RPC_URL"))
        self.w3 = Web3(MANTA_RPC_URL)
        self.admin_private_key=os.getenv("PRIVATE_KEY")

    async def create_wallet(self, user_address):
        existing_data = await self._load_existing_data()
        
        for entry in existing_data:
            if entry["user_address"] == user_address:
                print(f"Wallet already exists for user address: {user_address}")
                return
        
        private_key = self.w3.eth.account.create()._private_key.hex()
        await self.save_wallet_data(private_key, user_address)
        

    async def save_wallet_data(self, private_key, user_address):
        output_data = {
            "user_address": user_address,
            "data": private_key
        }

        existing_data = await self._load_existing_data()
        existing_data.append(output_data)
        await self._save_data(existing_data)
        print("Wallet data saved successfully.")

    async def fetch_data(self, user_address):
        existing_data = await self._load_existing_data()

        for entry in existing_data:
            if entry["user_address"] == user_address:
                private_key = entry["data"]
                
                return private_key

        print(f"No wallet data found for user address: {user_address}")
        return None
    
    async def _check_address(self, user_address):
        private_key = await self.fetch_data(user_address)
        account = Web3().eth.account.from_key(private_key)
        return account.address
    
    async def _fund_wallet(self, user_address):
        private_key = await self.fetch_data(user_address)

        sender_address = self.w3.eth.account.from_key(self.admin_private_key).address
        receiver_address = self.w3.eth.account.from_key(private_key).address
        
        nonce = self.w3.eth.get_transaction_count(sender_address)
        transaction = {
            'to': receiver_address,
            'value': self.w3.to_wei(0.0001, 'ether'),
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'chainId': 50002,
        }

        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"

    
    async def _transfer(self, user_address, amount, asset_id, destination):
        amount = amount * 10 ** 6
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(self.admin_private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=self._read_abi("abi/MockToken.json"))
    
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.transfer(destination, amount).build_transaction({
            'nonce': nonce,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': 50002,
        })

        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def _get_token_ca(self, asset_id):
        match asset_id:
            case "usdc":
                return "0xa0471Db84Fd1A7094d46C06F73304aA2D7129CD3"
            case "uni":
                return "0x49eA216d189B9E799711Fb78853c1dA85F2FECd5"
            case "weth":
                return "0xeC179Cb8CD08171449A6Ab47f1fbEbDf781f7De5"
            case "usdt":
                return "0x693e493B99fdeeb524b056213FC3c0847d8Da4bc"
            case "dai":
                return "0x3C60fA815cb652dc593dcB709BEc27b6A57fC41f"
    
    async def _get_protocol_ca(self, protocol):
        match protocol:
            case "uniswap":
                return "0x77Ab4Df809ba5D432d209df0A427Dd06730438b6"
            case "compoundv3":
                return "0x135F2c540e8b95682D2C726c1cB0dB2f4929fe5B"
            case "usdxmoney":
                return "0xe334318C2c027f1714449eEa4757A692d2defD55"
            case "stargatev3":
                return "0x80D7F2AC11Bf1cfe7f534df9d2E1CEA50BC4ee50"
            case "aavev3":
                return "0x766134D501efe40F9f3feb9df5dD3E333d4be9CC"
    
    async def mint(self, user_address, asset_id, amount):
        amount = int(amount) * (10 ** 6)
        abi = await self._read_abi("./abi/MockToken.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.mint(sender_address, amount).build_transaction({
            'chainId': 50002,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def transfer(self, user_address, contract_address, to, amount):
        amount = int(amount) * (10 ** 6)
        abi = await self._read_abi("./abi/MockToken.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.transfer(to, amount).build_transaction({
            'chainId': 50002,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def swap(self, user_address, spender, token_in, token_out, amount):
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        amount_generalized = int(amount) * (10 ** 6)
        
        status = await self.approve(sender_address, private_key, spender, token_in, amount)
        if status:
            abi = await self._read_abi("./abi/OptiFinance.json")
            
            staking_contract = self.w3.eth.contract(address="0x8021f46312E50dC3DA76Db701a63858c7a3415c1", abi=abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = staking_contract.functions.swap(token_in, token_out, amount_generalized).build_transaction({
                'chainId': 50002,
                'gas': 1000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return f"0x{tx_hash.hex()}"
        else:
            return f"Error during transaction"
    
    async def approve(self, sender_address, private_key, spender, token_in, amount):
        try:
            approve_abi = await self._read_abi("./abi/MockToken.json")
            amount = int(amount) * (10 ** 6)
            
            token_contract = self.w3.eth.contract(address=token_in, abi=approve_abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
                'chainId': 50002,
                'gas': 1000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return True
        
        except Exception as e:
            return False
    
    async def stake(self, user_address, asset_id, protocol, spender, amount):
        approve_abi = await self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=approve_abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
            'chainId': 50002,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        #=========================================================
        
        abi = await self._read_abi("./abi/MockStake.json")
        
        contract_address = await self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.stake(0, amount).build_transaction({
            'chainId': 50002,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    
    async def unstake(self, user_address, protocol):        
        abi = await self._read_abi("./abi/MockStake.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.withdrawAll().build_transaction({
            'chainId': 50002,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"


    async def _read_abi(self, abi_path):
        with open(abi_path, 'r') as file:
            return orjson.loads(file.read())


    async def _load_existing_data(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'rb') as file:
            return orjson.loads(file.read())

    async def _save_data(self, data):
        with open(self.file_path, 'wb') as file:
            file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
