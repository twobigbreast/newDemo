package com.litianyi.prpo;

import java.util.ArrayList;
import java.util.List;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/11 16:06
 * @Description:
 */
public class SD {

    private static List<Integer> counts=new ArrayList<>();


    public static void main(String[] args) {
        for (int i = 0; i < 11; i++) {
            counts.add(i);
        }
    }

    public static void doSomeThing() {

        if (counts.size()>4){

            System.out.println("容器已满了");
        }
    }
}
