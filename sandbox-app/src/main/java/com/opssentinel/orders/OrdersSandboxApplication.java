package com.opssentinel.orders;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * The sandbox app Ops Sentinel observes.
 *
 * <p>Deliberately small — a handful of Orders endpoints. It exists to generate real,
 * controllable incidents for the agent pipeline to react to, not to be interesting itself.
 * The domain is not the point.
 */
@SpringBootApplication
public class OrdersSandboxApplication {

  public static void main(String[] args) {
    SpringApplication.run(OrdersSandboxApplication.class, args);
  }
}
