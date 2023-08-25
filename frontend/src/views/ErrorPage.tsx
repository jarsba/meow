import React from "react";
import { useRouteError } from "react-router-dom";

export default function ErrorPage() {
    const error: any = useRouteError();

    return (
        <div id="error-page" className="flex flex-col w-screen h-screen justify-center">
            <div className="self-center">
                <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">Oops!</h1>
                <h2 className="scroll-m-10 text-2xl font-extrabold tracking-tight lg:text-2xl">Sorry, an unexpected error has occurred.</h2>
                <p>
                    <i>{error.statusText || error.message}</i>
                </p>
            </div>
        </div>
    );
}