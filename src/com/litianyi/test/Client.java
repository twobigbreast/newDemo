package com.litianyi.test;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/15 11:05
 * @Description:
 */
public class Client {
    public static void main(String[] args) {
        BlockingQueue<String> queue = new ArrayBlockingQueue<>(100);
        Comsumer comsumer = new Comsumer(queue);
        Product product1 = new Product(queue,"张三");
        Product product2 = new Product(queue,"李四");
        Product product3 = new Product(queue,"王五");

        new Thread(product1).start();
        new Thread(product2).start();
        new Thread(product3).start();
        //new Thread(comsumer).start();


    }
}
