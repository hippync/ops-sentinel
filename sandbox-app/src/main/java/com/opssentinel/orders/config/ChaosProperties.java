package com.opssentinel.orders.config;

import jakarta.annotation.PostConstruct;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Chaos endpoint configuration, validated at startup so it fails closed.
 *
 * <p>The previous default was an empty API key. A naive {@code equals} comparison against
 * {@code ""} means a request carrying an empty header authenticates — the classic fail-open
 * bug, in the one part of this app that can deliberately break production.
 *
 * <p>So: if chaos is enabled and the key is blank or too short, the application refuses to
 * boot. A container that will not start is a loud, obvious failure; a chaos endpoint that
 * accepts empty credentials is a silent one.
 */
@Component
@ConfigurationProperties(prefix = "opssentinel.chaos")
public class ChaosProperties {

  /** Minimum length that makes brute force impractical; not a substitute for a real secret store. */
  private static final int MIN_KEY_LENGTH = 32;

  private boolean enabled = false;
  private String adminApiKey = "";

  @PostConstruct
  void validate() {
    if (!enabled) {
      return;
    }
    if (adminApiKey == null || adminApiKey.isBlank()) {
      throw new IllegalStateException(
          "opssentinel.chaos.enabled=true but no admin API key is set. "
              + "Refusing to start: an empty key would authenticate an empty header.");
    }
    if (adminApiKey.length() < MIN_KEY_LENGTH) {
      throw new IllegalStateException(
          "Chaos admin API key must be at least " + MIN_KEY_LENGTH + " characters; got "
              + adminApiKey.length() + ".");
    }
  }

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public String getAdminApiKey() {
    return adminApiKey;
  }

  public void setAdminApiKey(String adminApiKey) {
    this.adminApiKey = adminApiKey;
  }
}
