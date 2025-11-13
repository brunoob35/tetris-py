CREATE DATABASE IF NOT EXISTS tetris_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE tetris_db;

-- 1) Usuários
CREATE TABLE users (
                       id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                       username VARCHAR(50) NOT NULL UNIQUE,
                       email VARCHAR(255) NULL,
                       password_hash VARCHAR(255) NOT NULL,
                       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2) Partidas
CREATE TABLE games (
                       id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                       user_id BIGINT UNSIGNED NOT NULL,
                       started_at DATETIME(6) NOT NULL,
                       finished_at DATETIME(6) NULL,
                       final_score INT NOT NULL DEFAULT 0,
                       lines_cleared INT NOT NULL DEFAULT 0,
                       level_reached INT NOT NULL DEFAULT 1,
                       duration_ms INT NOT NULL DEFAULT 0,
                       rng_seed BIGINT NULL,
                       status ENUM('in_progress','completed','abandoned') NOT NULL DEFAULT 'in_progress',
                       created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                       CONSTRAINT fk_games_user FOREIGN KEY (user_id)
                           REFERENCES users(id)
                           ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_games_user ON games(user_id);
CREATE INDEX idx_games_score ON games(final_score);
CREATE INDEX idx_games_status ON games(status);

-- 3) Saves (estado para continuar depois)
CREATE TABLE saved_games (
                             id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                             user_id BIGINT UNSIGNED NOT NULL,
                             game_id BIGINT UNSIGNED NULL,
                             state_json JSON NOT NULL,
                             is_active TINYINT(1) NOT NULL DEFAULT 1,
                             created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                             updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
                             CONSTRAINT fk_saved_user FOREIGN KEY (user_id)
                                 REFERENCES users(id)
                                 ON DELETE CASCADE,
                             CONSTRAINT fk_saved_game FOREIGN KEY (game_id)
                                 REFERENCES games(id)
                                 ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_saved_user_active
    ON saved_games(user_id, is_active);

-- 4) Replays
CREATE TABLE game_replays (
                              id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                              game_id BIGINT UNSIGNED NOT NULL,
                              replay_data LONGTEXT NOT NULL, -- JSON com a lista de eventos
                              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                              CONSTRAINT fk_replay_game FOREIGN KEY (game_id)
                                  REFERENCES games(id)
                                  ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_replay_game ON game_replays(game_id);

-- 5) High scores
CREATE TABLE user_high_scores (
                                  user_id BIGINT UNSIGNED PRIMARY KEY,
                                  best_score INT NOT NULL,
                                  best_score_at DATETIME(6) NOT NULL,
                                  CONSTRAINT fk_highscores_user FOREIGN KEY (user_id)
                                      REFERENCES users(id)
                                      ON DELETE CASCADE
) ENGINE=InnoDB;
