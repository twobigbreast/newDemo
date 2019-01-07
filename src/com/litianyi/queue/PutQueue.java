package com.litianyi.queue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/20 14:11
 * @Description:
 */
public class PutQueue implements Runnable {

    private BlockingQueue<Integer> queue;

    public PutQueue(BlockingQueue<Integer> queue) {
        this.queue = queue;
    }

    public void addElements(Integer i) throws InterruptedException {
        queue.put(i);

        if (queue.size()>=10000){
            System.out.println("元素不够用了");
            Thread.sleep(3000);
            System.out.println("还剩："+queue.size()+"个元素");
            List<Integer> list = new ArrayList<>(10000);
            queue.drainTo(list);
            Thread.sleep(3000);
            System.out.println("新连表中有："+list.size()+"个元素");
            queue.clear();
        }
    }



    @Override
    public void run() {
        for (int i = 0; i < 2700; i++) {
            try {
                addElements(i);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }
}
