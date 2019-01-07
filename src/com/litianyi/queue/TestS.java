package com.litianyi.queue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/20 14:16
 * @Description:
 */
public class TestS {

    public static void main(String[] args) {
        BlockingQueue<Integer> queue=new ArrayBlockingQueue<Integer>(10000);


        for (int i = 0; i < 5; i++) {
            PutQueue target = new PutQueue(queue);
            new Thread(target).start();
        }

    }

    /*public static void main(String[] args) {
        List<Integer> list = new ArrayList<>(1);
        for (int i = 0; i < 10; i++) {
            list.add(i);
        }
        for (Integer integer : list) {
            System.out.println(integer);
        }
    }*/
}
