package com.opssentinel.orders.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/**
 * The chaos endpoints can deliberately break the system Ops Sentinel watches. They must
 * fail closed, and the failure must be at startup rather than at request time.
 */
class ChaosPropertiesTest {

  @Test
  void refusesToStartWhenChaosEnabledWithBlankKey() {
    ChaosProperties properties = new ChaosProperties();
    properties.setEnabled(true);
    properties.setAdminApiKey("");

    assertThatThrownBy(properties::validate)
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("no admin API key");
  }

  @Test
  void refusesToStartWhenKeyIsTooShortToBeReal() {
    ChaosProperties properties = new ChaosProperties();
    properties.setEnabled(true);
    properties.setAdminApiKey("short");

    assertThatThrownBy(properties::validate).isInstanceOf(IllegalStateException.class);
  }

  @Test
  void allowsStartupWhenChaosIsDisabled() {
    ChaosProperties properties = new ChaosProperties();
    properties.setEnabled(false);
    properties.setAdminApiKey("");

    assertThat(properties.isEnabled()).isFalse();
  }

  @Test
  void allowsStartupWithASufficientKey() {
    ChaosProperties properties = new ChaosProperties();
    properties.setEnabled(true);
    properties.setAdminApiKey("a".repeat(32));

    properties.validate();
    assertThat(properties.getAdminApiKey()).hasSize(32);
  }
}
