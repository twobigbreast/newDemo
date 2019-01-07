package com.litianyi.list;

import java.util.List;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/20 14:49
 * @Description:
 */
public class MyList implements Runnable {

    private List<Integer> list;

    public MyList(List<Integer> list) {
        this.list = list;
    }

    @Override
    public void run() {
        for (int i = 0; i < 1000; i++) {
            list.add(i);
            if (list.size()==3500){
                System.out.println("不够用了，清除元素"+list.size());
                list.clear();
                System.out.println("元素还剩"+list.size());

            }
        }
    }
}
