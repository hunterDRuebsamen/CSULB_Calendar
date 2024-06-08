import multiprocessing
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from .classes.month import CalMonth
from .classes.year import CalYear, Calendar_Input
from fastapi.responses import StreamingResponse
import base64
import io
import time
import itertools
from shared_memory_dict import SharedMemoryDict
import logging

# https://www.geeksforgeeks.org/python-requests-tutorial/#

THREADS = 4

app = FastAPI()

class Month(BaseModel):
    month: int = 1
    day_colors : list | None = ['red','blue']

class Base_Input(BaseModel):
    month: int
    day : int 
    year: int
    
@app.post("/calendar/test")
async def testThree(req : Month):
    return {
                "message": "hello world",
                "day_colors": req.day_colors
            }

@app.post("/calendar/table")
async def testTwo(req : Month):
    year = CalYear()
    awd_fall = [12, 21, 22, 19, 19]
    id_fall = [6, 21, 22, 16, 9]
    months = ['Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    img = year.create_months_table(awd=awd_fall, id=id_fall, months=months)
    
    # Save the PIL image to a BytesIO object
    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format='PNG')
    
    # Rewind the BytesIO object to the start
    img_bytes_io.seek(0)

    # Return a StreamingResponse object
    return StreamingResponse(img_bytes_io, media_type="image/png")

@app.post("/calendar/month")
async def testOne(req : Calendar_Input):
    cmonth = CalMonth(req.year, req.month)
    img = cmonth.draw(req.width)
    # Save the PIL image to a BytesIO object
    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format='PNG')
    
    # Rewind the BytesIO object to the start
    img_bytes_io.seek(0)
    
    # Return a StreamingResponse object
    return StreamingResponse(img_bytes_io, media_type="image/png")

@app.post("/calendar/build_year")
async def build_year(req : Calendar_Input):    
    start = time.perf_counter()
    calyear = CalYear(req)
    if calyear.valid:
        result_image = calyear.gen_schedule()
    
        # Save the PIL image to a BytesIO object
        img_bytes_io = io.BytesIO()
        result_image.save(img_bytes_io, format='PNG')
        
        # Rewind the BytesIO object to the start
        img_bytes_io.seek(0)
        
        end = time.perf_counter()
        print("Elapsed (time) = {}s".format((end - start)))
        # Return a StreamingResponse object
        return StreamingResponse(img_bytes_io, media_type="image/png")
    return None

@app.post("/calendar/build_years_test")
def build_years_request2(req : Calendar_Input):    
    result = []
    calyear = CalYear(req)
    cnt=0

    # set conditions
    awd = 172
    id = 148
    convo_day = 3
    winter_sess = 13

    print(f"\nGenerating calendar {cnt}")
    start = time.perf_counter()
    result_image, a = calyear.gen_schedule(awd, id, convo_day, winter_sess)
    cnt += 1
    if result_image == None:
        # result.append({"image": None})
        pass
    else:
        # Save the PIL image to a BytesIO object
        img_bytes_io = io.BytesIO()
        result_image.save(img_bytes_io, format='PNG')
        img_str = base64.b64encode(img_bytes_io.getvalue()).decode("utf-8")
        returndict = {"image": img_str}
        result.append(returndict)
    end = time.perf_counter()
    print("Elapsed (time) = {}s".format((end - start)))
        
    return result

@app.post("/calendar/build_years_sequential")
def build_years_request2(req : Calendar_Input):    
    result = []
    calyear = CalYear(req)
    result_dict = {}
    cnt=0
    for awd in range(170, 181):
        for id in range(145, 150):
            for convo_day in range(2, 6):
                for winter_sess in range(12, 16):
                    print(f"\nGenerating calendar {cnt}")
                    start = time.perf_counter()
                    result_image, md5_hash = calyear.gen_schedule(awd, id, convo_day, winter_sess)
                    if md5_hash in result_dict:
                        result_image = None
                        print("Duplicate calendar, discarded")
                    else:
                        result_dict[md5_hash] = True
                    cnt += 1
                    if result_image == None:
                        # result.append({"image": None})
                        pass
                    else:
                        # Save the PIL image to a BytesIO object
                        img_bytes_io = io.BytesIO()
                        result_image.save(img_bytes_io, format='PNG')
                        img_str = base64.b64encode(img_bytes_io.getvalue()).decode("utf-8")
                        returndict = {"image": img_str}
                        result.append(returndict)
                    end = time.perf_counter()
                    print("Elapsed (time) = {}s".format((end - start)))
        
    return result

@app.post("/calendar/build_years")
def build_years_request(req: Calendar_Input):
    result_dict = {}
    results = []

    args_list = [
        (i, awd, id, convo_day, winter_sess)
        for i, (awd, id, convo_day, winter_sess) in enumerate(
            itertools.product(range(170, 181), range(145, 150), range(2, 6), range(12, 16))
        )
    ]

    for args in args_list:
        idx, awd, id, convo_day, winter_sess = args
        print(f"Processing calendar {idx}")
        calyear = CalYear(req)  # Initialize CalYear inside the loop to ensure a fresh instance each time

        # Adding detailed debug information
        print(f"CalYear initialized with start_date: {calyear.start_date}")
        print(f"CalYear initialized with fall_semester_start: {calyear.fall_semester_start}")
        print(f"CalYear initialized with summer_session_start: {calyear.summer_session_start}")
        print(f"CalYear initialized with commencement_end: {calyear.commencement_end}")

        if not calyear.valid:
            print(f"Invalid CalYear for calendar {idx}")
            continue

        # Detailed debug information for compute_awd
        awd_success = calyear.compute_awd(awd)
        if not awd_success:
            print(f"Error: Not enough AWD to build Calendar {idx}")
            continue

        result_image, md5_hash = calyear.gen_schedule(awd, id, convo_day, winter_sess)
        if md5_hash in result_dict:
            result_image = None
            print("Duplicate calendar, discarded")
        else:
            result_dict[md5_hash] = True

        if result_image is None:
            results.append({"image": None})
        else:
            img_bytes_io = io.BytesIO()
            result_image.save(img_bytes_io, format='PNG')
            img_str = base64.b64encode(img_bytes_io.getvalue()).decode("utf-8")
            results.append({"image": img_str})

        if len(results) % 10 == 0:
            logging.debug(f"Processed {len(results)} calendars")

    return results



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)