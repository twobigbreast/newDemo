package com.litianyi.test;

import java.util.concurrent.BlockingQueue;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/15 10:59
 * @Description:
 */
public class Comsumer implements Runnable{

    private BlockingQueue<String> queue;


    public Comsumer(BlockingQueue<String> queue) {
        this.queue = queue;
    }

    @Override
    public void run() {
       while (true){
           if (queue.size()>=99){
               queue.clear();
               System.out.println("队列被清楚了");
           }
       }
    }
}
