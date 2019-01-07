package com.litianyi.test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.atomic.AtomicReference;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/15 10:56
 * @Description:
 */
public class Product implements Runnable {

    private BlockingQueue<String> queue;

    private String name;

    private Object lock = new Object();

    private AtomicReference<List> reference = new AtomicReference<>();

    public Product(BlockingQueue<String> queue, String name) {
        this.queue = queue;
        this.name = name;
    }

    @Override
    public void run() {
        try {
            for (int i = 0; i < 100; i++) {
                Thread.sleep(100);
                queue.put(name + "" + i);
                System.out.println("我放入了一些值" + name + "" + i);

                if (queue.size() >= 99) {

                    System.out.println("我把队列清楚了" + queue.size());
                   final ArrayList<String> c = new ArrayList<>(queue.size());
                    int i1 = queue.drainTo(c);
                    queue.clear();
                    System.out.println(i1);

                }
            }


        } catch (InterruptedException e) {
            e.printStackTrace();
        }

    }
}
