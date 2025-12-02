# 🐍 PyRecurse: Python Recursive DNS Resolver

Recursive DNS Resolver from scratch in Python built to understand how DNS resolution works under the hood!

This project implements a functional DNS server that can be used as a dns server replacing your bullshit ISP's that do not respect ttl.

It features **TTL-respecting caching**, robust logging, and handles glue records/intermediate nameserver resolution.

## ✨ Features

  * **Full Recursion:** Resolves domains starting from the 13 Root Servers.
  * **Smart Caching:** Implements an in-memory cache that respects the `TTL` (Time To Live) of records.
  * **Deep Logging:** visualizes the entire journey of a DNS packet (Referrals, Glue Records, Answers).
  * **Glue Record Handling:** Automatically detects and resolves required Name Server IPs during recursion.
  * **Protocol Compliance:** Uses `dnslib` for safe packet parsing/packing (replacing raw bitwise operations).

## 🛠️ Installation

1.  **Clone the repository** (or create the file):

    ```bash
    git clone https://github.com/yourusername/dns-resolver.git
    cd dns-resolver
    ```

2.  **Install Dependencies:**
    We use `dnslib` to handle the binary packet parsing.

    ```bash
    pip install dnslib
    ```

## 🚀 Usage

DNS servers run on **Port 53**, which is a privileged port. You must run the script with `sudo` (or Administrator privileges).

```bash
sudo python3 main.py
```

*The server will start listening on `127.0.0.1:53`.*

-----

## 📺 Demo

### 1\. The "Cold" Query (Full Recursion)

**Client Command:**
Asking for `buddhag.com.np` for the first time.

```bash
dig @127.0.0.1 buddhag.com.np
```

**Server Logs:**
The server traverses the internet hierarchy step-by-step.

```text
--- New Query: buddhag.com.np. ---
10:20:01 - [Step 1] - Starting recursion for buddhag.com.np. at Root: 198.41.0.4
10:20:01 - [Step 1] - Referral: buddhag.com.np. -> np.
10:20:02 - [Step 1] - Glue record found: np. -> 196.19.0.1
10:20:02 - [Step 1] - Referral: buddhag.com.np. -> mos.com.np.
10:20:02 - [Step 1] - No Glue! Suspending query to resolve nameserver: mos.com.np.
10:20:03 - [Step 2] - ... Resolved nameserver mos.com.np. to 202.52.2.2
10:20:03 - [Step 1] - Answer received from 202.52.2.2
```

### 2\. The "Warm" Query (Cache Hit)

**Client Command:**
Asking for the same domain 10 seconds later.

```bash
dig @127.0.0.1 buddhag.com.np
```

**Server Logs:**
The server serves the record instantly from memory, adjusting the TTL.

```text
--- New Query: buddhag.com.np. ---
10:20:11 - [Step 1] - CACHE HIT: buddhag.com.np. (TTL: 290s)
```

-----

## 🧠 How it Works

1.  **Request:** The server receives a UDP packet on port 53.
2.  **Cache Check:** It checks if the domain exists in the local dictionary and if the `expiry_time > current_time`.
      * *If Hit:* It performs a **Deep Copy** of the record, updates the TTL field, and sends it.
3.  **Root Referral:** If not in cache, it asks a hardcoded Root Server (e.g., `198.41.0.4`).
4.  **The Loop:**
      * If the server returns an **Answer**: Cache it and return to client.
      * If the server returns a **Referral (NS Record)**: Update the target IP and loop again.
      * If the Referral has **No Glue**: Pause the current task, start a new recursion to find the IP of the Name Server, then resume.

## Replacing your local DNS server 
- Visualize the hundreds of queries that happen even when you aren't browsing anything
- To change your DNS server to localhost, you can modify your network settings

## 📄 License

MIT
