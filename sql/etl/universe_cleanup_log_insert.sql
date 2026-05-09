-- Append a row to universe_cleanup_log.
-- Params: 1=exchange, 2=total_processed, 3=valid_count, 4=invalid_count, 5=notes.
INSERT INTO universe_cleanup_log (exchange, total_processed, valid_count, invalid_count, notes)
VALUES (%s, %s, %s, %s, %s)
