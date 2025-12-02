import socket
import copy  # Make sure this is imported at the top!
import logging
import time
from dnslib import DNSRecord, QTYPE, RR, A
from dnslib.server import DNSServer, BaseResolver, DNSHandler
# Update this line to include DNSQuestion
from dnslib import DNSRecord, QTYPE, RR, A, DNSQuestion

# --- CONFIGURATION ---
PORT = 53
IP = "127.0.0.1"
ROOT_SERVERS = ["198.41.0.4"]  # a.root-servers.net

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Step %(step)d] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DNS")


class Cache:
    """Corrected Cache with Deep Copy support"""
    def __init__(self):
        self.store = {}

    def get(self, qname, qtype):
        key = (str(qname), qtype)
        if key in self.store:
            expiry, record = self.store[key]
            now = time.time()
            
            if now < expiry:
                remaining_ttl = int(expiry - now)
                
                # --- THE FIX ---
                # We deepcopy the record so we don't need to rebuild it manually.
                # This avoids the "attribute name must be string" error.
                response_copy = copy.deepcopy(record)
                
                # Update TTLs in the copy
                for rr in response_copy.rr:
                    rr.ttl = remaining_ttl
                for rr in response_copy.auth:
                    rr.ttl = remaining_ttl
                for rr in response_copy.ar:
                    rr.ttl = remaining_ttl
                    
                return response_copy
            else:
                del self.store[key] # Expired
        return None

    def add(self, qname, qtype, record, ttl):
        key = (str(qname), qtype)
        expiry = time.time() + ttl
        self.store[key] = (expiry, record)

class RecursiveResolver:
    def __init__(self):
        self.cache = Cache()
    
    # query_remote remains the same as your fixed version...
    def query_remote(self, qname, qtype, server_ip):
        try:
            q = DNSQuestion(qname, qtype)
            request = DNSRecord(q=q)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(request.pack(), (server_ip, 53))
            data, _ = sock.recvfrom(2048)
            sock.close()
            return DNSRecord.parse(data)
        except Exception as e:
            logger.error(f"Failed to query {server_ip}: {e}", extra={'step': 0})
            return None

    def resolve(self, qname, qtype, step=1):
        """Updated Resolve Logic"""
        
        # 1. Check Cache
        # Since Cache.get now handles the copying, we just return the result.
        # No need to manually create DNSRecord() or call DNSRecord.question()
        cached_response = self.cache.get(qname, qtype)
        
        if cached_response:
            logger.info(f"CACHE HIT: {qname}", extra={'step': step})
            return cached_response

        # 2. Start Recursion (Logic remains the same)
        candidate_server = ROOT_SERVERS[0]
        logger.info(f"Starting recursion for {qname} at Root: {candidate_server}", extra={'step': step})

        while True:
            response = self.query_remote(qname, qtype, candidate_server)
            if not response:
                break

            if response.rr:
                logger.info(f"Answer received from {candidate_server}", extra={'step': step})
                min_ttl = min([r.ttl for r in response.rr], default=60)
                self.cache.add(qname, qtype, response, min_ttl)
                return response
            
            elif response.auth:
                ns_rr = response.auth[0]
                ns_name = str(ns_rr.rdata)
                logger.info(f"Referral: {qname} -> {ns_name}", extra={'step': step})

                glue_ip = None
                for ar in response.ar:
                    if str(ar.rname) == ns_name and ar.rtype == QTYPE.A:
                        glue_ip = str(ar.rdata)
                        break
                
                if glue_ip:
                    candidate_server = glue_ip
                else:
                    logger.info(f"Resolving nameserver: {ns_name}", extra={'step': step})
                    # Recursive call
                    ns_response = self.resolve(ns_name, QTYPE.A, step=step+1)
                    if ns_response and ns_response.rr:
                        candidate_server = str(ns_response.rr[0].rdata)
                    else:
                        break
            else:
                break
        
        return None

# --- UDP SERVER HANDLER ---
# This part simply listens on localhost:53 and calls our Resolver
def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))
    print(f"Recursive DNS Server listening on {IP}:{PORT}...")
    
    resolver = RecursiveResolver()

    while True:
        data, addr = sock.recvfrom(512)
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname)
            qtype = request.q.qtype
            
            print(f"\n--- New Query: {qname} ---")
            
            # Perform Recursion
            reply = resolver.resolve(qname, qtype)
            
            if reply:
                # Match the transaction ID of the request
                reply.header.id = request.header.id
                reply.header.qr = 1 # It's a response
                reply.header.ra = 1 # Recursion Available
                
                sock.sendto(reply.pack(), addr)
            else:
                logger.error("Failed to resolve", extra={'step': 999})
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    start_server()
