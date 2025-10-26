import logging
import uuid
import time
from threading import Thread

logger = logging.getLogger(__name__)

class LeaderElection:
    def __init__(self, pg_connector):
        self.pg_connector = pg_connector
        self.bot_id = str(uuid.uuid4())
        self._is_leader = False
        self.advisory_lock_id = 12345 # A unique integer for our application's lock

    def attempt_to_become_leader(self):
        """Tries to acquire the leader lock using an advisory lock. Returns True if successful."""
        try:
            self.pg_connector._ensure_connection()
            with self.pg_connector.conn.cursor() as cur:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (self.advisory_lock_id,))
                lock_acquired = cur.fetchone()[0]

                if lock_acquired:
                    logger.info(f"Bot {self.bot_id} successfully acquired the advisory lock.")
                    # Now that we have the lock, update the table to reflect our leadership
                    cur.execute("UPDATE leader_election SET leader_id = %s, last_heartbeat = NOW() WHERE id = 1", (self.bot_id,))
                    self.pg_connector.conn.commit()
                    self._is_leader = True
                    logger.info(f"Bot {self.bot_id} has become the LEADER.")
                    return True
                else:
                    logger.info(f"Bot {self.bot_id} could not acquire advisory lock. Will become a FOLLOWER.")
                    self._is_leader = False
                    return False
        except Exception as e:
            logger.error(f"An error occurred while trying to become leader: {e}", exc_info=True)
            # Ensure we roll back any partial transaction
            if self.pg_connector.conn:
                self.pg_connector.conn.rollback()
            self._is_leader = False
            return False

    def release_lock(self):
        """Releases the advisory lock, typically on shutdown."""
        if not self._is_leader:
            return # Only leaders can release the lock
        try:
            logger.info(f"Leader {self.bot_id} is shutting down and releasing the lock.")
            self.pg_connector._ensure_connection()
            with self.pg_connector.conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (self.advisory_lock_id,))
                self.pg_connector.conn.commit()
                logger.info("Advisory lock released successfully.")
        except Exception as e:
            logger.error(f"An error occurred while releasing the advisory lock: {e}", exc_info=True)


    def is_leader(self):
        return self._is_leader

    def start_heartbeat(self):
        """Starts a background thread to send heartbeats."""
        if not self._is_leader:
            logger.warning("Cannot start heartbeat thread because this bot is not the leader.")
            return

        heartbeat_thread = Thread(target=self._send_heartbeat, daemon=True)
        heartbeat_thread.start()
        logger.info(f"Heartbeat thread started for leader {self.bot_id}.")

    def _send_heartbeat(self):
        """Periodically updates the heartbeat timestamp in the database."""
        while self._is_leader:
            try:
                self.pg_connector._ensure_connection()
                with self.pg_connector.conn.cursor() as cur:
                    cur.execute("UPDATE leader_election SET last_heartbeat = NOW() WHERE id = 1 AND leader_id = %s", (self.bot_id,))
                    self.pg_connector.conn.commit()
                time.sleep(5) # Send heartbeat every 5 seconds
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                self._is_leader = False # Step down as leader if heartbeat fails
                break

    def monitor_leader(self):
        """Monitors the leader's heartbeat and attempts to take over if the leader fails."""
        logger.info(f"Bot {self.bot_id} is in follower mode. Monitoring leader...")
        while not self._is_leader:
            try:
                self.pg_connector._ensure_connection()
                with self.pg_connector.conn.cursor() as cur:
                    cur.execute("SELECT leader_id, last_heartbeat FROM leader_election WHERE id = 1")
                    result = cur.fetchone()
                    if result:
                        leader_id, last_heartbeat = result
                        # Check if leader is missing or heartbeat is stale (e.g., > 15 seconds)
                        if leader_id is None or (last_heartbeat and (time.time() - last_heartbeat.timestamp()) > 15):
                            logger.warning("Leader is down or heartbeat is stale. Attempting to become the new leader...")
                            if self.attempt_to_become_leader():
                                # If successful, the loop will terminate as self._is_leader becomes True
                                pass
            except Exception as e:
                logger.error(f"Error while monitoring leader: {e}")

            time.sleep(10) # Check every 10 seconds
