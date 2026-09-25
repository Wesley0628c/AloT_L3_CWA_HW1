// Isolated and terminated by the caller when a query exceeds its time budget.
importScripts('./vendor/sql-wasm.js');
onmessage = async ({data}) => {
    let db,statement;
    try {
        if (!/^SELECT\b/i.test(data.query.trim()) || data.query.length>4000) throw new Error('僅允許 SELECT');
        const SQL = await initSqlJs({locateFile:file=>new URL('./vendor/'+file,self.location.href).href});
        const response=await fetch(data.database,{cache:'no-store'});
        if (!response.ok) throw new Error('預報資料庫載入失敗');
        db=new SQL.Database(new Uint8Array(await response.arrayBuffer()));
        db.run('PRAGMA query_only=ON');
        statement=db.prepare(data.query);
        const rows=[];
        while(rows.length<500 && statement.step()) rows.push(statement.getAsObject());
        postMessage({result:{count:rows.length,results:rows,limit:500}});
    } catch (error) {postMessage({error:error.message});}
    finally {if(statement)statement.free();if(db)db.close();}
};
