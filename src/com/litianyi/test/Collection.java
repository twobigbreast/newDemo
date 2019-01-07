package com.litianyi.test;

import java.util.ArrayList;
import java.util.List;

/**
 * @Auther: ICC18e697
 * @Date: 2019/1/4 15:36
 * @Description:
 */

public class Collection {

    public static void main(String[] args) {
        ArrayList<Integer> list = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            list.add(i);
        }

        List<List<Integer>> lists = averageAssign(list, 3);
        for (List<Integer> integers : lists) {
            System.out.println(integers.toString());
        }

    }


    /**
     * 将一个list均分成n个list,主要通过偏移量来实现的
     * @param source
     * @return
     */
    public static <T> List<List<T>> averageAssign(List<T> source,int n) {
        List<List<T>> result = new ArrayList<>();
        int remaider = source.size() % n;  //(先计算出余数)
        int number = source.size() / n;  //然后是商
        int offset = 0;//偏移量
        for (int i = 0; i < n; i++) {
            List<T> value = null;
            if (remaider > 0) {
                value = source.subList(i * number + offset, (i + 1) * number + offset + 1);
                remaider--;
                offset++;
            } else {
                value = source.subList(i * number + offset, (i + 1) * number + offset);
            }
            result.add(value);
        }
        return result;

    }
}
